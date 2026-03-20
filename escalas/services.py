from datetime import timedelta
from django.db import transaction
from .models import Escala, DiaEscala, TurnoEscala, AlocacaoEscala
from .utils import SeletorOperadores, puxar_da_fila, fila_operadores, pontuar_alocacao, escolher_reserva, escolher_titular_semana
from django.db import transaction
from accounts.models import User
from django.db.models import Q, Count
from django.db.models import Prefetch
from escalas.ia.runtime import fila_operadores_com_ia
from .fairness import puxar_da_fila_fair
from collections import deque

from pontuacao.utils import registrar_pontuacoes_em_lote
from django.core.exceptions import ValidationError

def ultimos_titulares(secao, semanas=1):
    from datetime import timedelta
    from django.utils import timezone

    data_limite = timezone.now().date() - timedelta(days=7 * semanas)

    return set(
        AlocacaoEscala.objects.filter(
            turno__dia__escala__secao=secao,
            tipo="TIT",
            turno__dia__escala__data_inicio__gte=data_limite,
        ).values_list("usuario_id", flat=True)
    )

def selecionar_titulares_semana(secao):
    fila = fila_operadores(secao)

    # 🔥 NOVO
    bloqueados = ultimos_titulares(secao)

    titulares = []
    fallback = []

    while fila and len(titulares) < 2:
        op = fila.popleft()

        if op.id in bloqueados:
            fallback.append(op)  # guarda pra depois
            continue

        titulares.append(op)

    # 🔥 se não conseguiu preencher (ex: poucos operadores)
    while len(titulares) < 2 and fallback:
        titulares.append(fallback.pop(0))

    return titulares, fila

def ja_escalado_no_dia(usuario_id, data, escala):
    return AlocacaoEscala.objects.filter(
        usuario_id=usuario_id,
        turno__dia__data=data,
        turno__dia__escala=escala,
    ).exists()

def acionar_sobreaviso(alocacao):
    """
    Apenas marca como acionado.
    A pontuação será registrada no encerramento da escala.
    """

    if alocacao.tipo != "SOBREAVISO":
        raise ValidationError("Alocação não é sobreaviso.")

    if alocacao.foi_acionado:
        return

    alocacao.foi_acionado = True
    alocacao.save()


TURNOS_PADRAO = ["MAD", "NOT"]

from django.db import transaction

def gerar_escala_semanal_fixa(dias, secao):
    titulares, fila = selecionar_titulares_semana(secao)

    for dia in dias:
        if dia.tipo_dia == "VERMELHA":
            continue

        usados_no_dia = set()

        for turno in dia.turnos.all():

            # quantidade por turno
            qtd = 1 if turno.turno in ["MAD", "NOT"] else 1
            # (ou usa qtd_madrugada / qtd_noturno se quiser evoluir depois)

            # =========================
            # TITULARES
            # =========================
            for _ in range(qtd):

                titular = escolher_titular_semana(
                    data=dia.data,
                    turno=turno,
                    titulares=titulares,
                    fila=fila,
                    usados_no_dia=usados_no_dia
                )

                if not titular:
                    continue

                usados_no_dia.add(titular.id)

                aloc = AlocacaoEscala.objects.create(
                    usuario=titular,
                    turno=turno,
                    tipo="TIT",
                    data=dia.data,
                )

                pontuar_alocacao(aloc)

            # =========================
            # RESERVA
            # =========================
            reserva = escolher_reserva(
                data=dia.data,
                turno=turno,
                fila=fila,
                usados_no_dia=usados_no_dia
            )

            if reserva:
                usados_no_dia.add(reserva.id)

                AlocacaoEscala.objects.create(
                    usuario=reserva,
                    turno=turno,
                    tipo="RES",
                    data=dia.data,
                )

@transaction.atomic
def gerar_escala_semanal(
    secao,
    data_inicio,
    criada_por,
    qtd_madrugada,
    qtd_noturno,
    modo="DIN"
):
    escala = Escala.objects.create(
        secao=secao,
        data_inicio=data_inicio,
        data_fim=data_inicio + timedelta(days=6),
        criada_por=criada_por,
    )

    fila_base = fila_operadores(secao)

    amarelos = []
    pretos = []

    # =========================
    # 1️⃣ Criar estrutura
    # =========================
    for i in range(7):
        data = data_inicio + timedelta(days=i)
        weekday = data.weekday()

        tipo_dia = (
            "PRETA" if weekday < 4
            else "AMARELA" if weekday == 4
            else "VERMELHA"
        )

        dia = DiaEscala.objects.create(
            escala=escala,
            data=data,
            tipo_dia=tipo_dia,
        )

        if tipo_dia == "VERMELHA":
            continue

        for turno_codigo in TURNOS_PADRAO:
            turno = TurnoEscala.objects.create(
                dia=dia,
                turno=turno_codigo,
            )

            registro = (data, turno_codigo, turno)

            if tipo_dia == "AMARELA":
                amarelos.append(registro)
            else:
                pretos.append(registro)
                
        if modo == "SEM":
            dias = escala.dias.prefetch_related("turnos__alocacoes")

            gerar_escala_semanal_fixa(
                dias=dias,
                secao=secao,
            )

            return escala

    # =========================
    # Helper justo
    # =========================
    def alocar_bloco(lista, fila, secao):
        usados_por_dia = {}

        for data, turno_codigo, turno in lista:
            usados_no_dia = usados_por_dia.setdefault(data, set())
            qtd = qtd_madrugada if turno_codigo == "MAD" else qtd_noturno

            for _ in range(qtd):
                op = puxar_da_fila_fair(fila, data, turno, usados_no_dia, secao)
                if not op:
                    break

                usados_no_dia.add(op.id)

                aloc = AlocacaoEscala.objects.create(
                    turno=turno,
                    usuario=op,
                    tipo="TIT",
                    data=data,
                )
                pontuar_alocacao(aloc)

        return usados_por_dia

    # =========================
    # 2️⃣ AMARELOS (fila isolada)
    # =========================
    fila_amarela = deque(fila_base)
    usados_amarelos = alocar_bloco(amarelos, fila_amarela, secao)

    # =========================
    # 3️⃣ PRETOS (fila continua)
    # =========================
    # começa de onde amarelo terminou → justiça semanal
    fila_preta = fila_amarela
    usados_pretos = alocar_bloco(pretos, fila_preta, secao)

    # =========================
    # VALIDAR NOT habilitado
    # =========================
    for data, turno_codigo, turno in amarelos + pretos:
        if turno_codigo != "NOT":
            continue

        tem_habilitado = turno.alocacoes.filter(
            usuario__cursos__codigo="MAN",
            tipo="TIT"
        ).exists()

        if not tem_habilitado:
            raise ValidationError(
                f"Turno noturno do dia {data} ficou sem habilitado."
            )

    # =========================
    # RESERVAS (justas)
    # =========================
    usados_global = {}

    for dicionario in (usados_amarelos, usados_pretos):
        for data, usados in dicionario.items():
            usados_global.setdefault(data, set()).update(usados)

    for data, turno_codigo, turno in amarelos + pretos:
        usados_no_dia = usados_global.setdefault(data, set())

        op = puxar_da_fila_fair(fila_preta, data, turno, usados_no_dia, secao)
        if not op:
            continue

        usados_no_dia.add(op.id)

        AlocacaoEscala.objects.create(
            turno=turno,
            usuario=op,
            tipo="RES",
            data=data,
        )

    return escala


@transaction.atomic
def encerrar_escala(escala, usuario):
    if escala.status != Escala.Status.PUBLICADA:
        raise ValueError("A escala precisa estar publicada.")

    if not usuario.pode_escalar():
        raise PermissionError("Sem permissão.")

    dias = escala.dias.prefetch_related(
        "turnos__alocacoes__usuario",
        "turnos__dia"
    )

    todas_alocacoes = []

    for dia in dias:
        for turno in dia.turnos.all():
            todas_alocacoes.extend(turno.alocacoes.all())

    registrar_pontuacoes_em_lote(todas_alocacoes)

    escala.status = Escala.Status.ENCERRADA
    escala.save()

@transaction.atomic
def criar_sobreaviso_service(secao, data, quantidade, criada_por):
    escala = Escala.objects.create(
        secao=secao,
        data_inicio=data,
        data_fim=data,
        criada_por=criada_por,
        tipo=Escala.Tipo.SOBREAVISO,
    )

    dia = DiaEscala.objects.create(
        escala=escala,
        data=data,
        tipo_dia="VERMELHA",
    )

    turno = TurnoEscala.objects.create(
        dia=dia,
        turno="SOB",
    )

    operadores = list(
        User.objects
        .filter(secao=secao, papel="OPE")
        .annotate(
            total_sobreaviso=Count(
                "alocacoes",
                filter=Q(alocacoes__tipo="SOB")
            )
        )
        .order_by("total_sobreaviso", "id")
    )

    seletor = SeletorOperadores(operadores)
    usados = set()

    for _ in range(quantidade):
        usuario = None

        for _ in range(len(operadores)):
            candidato = seletor.proximo(data, usados)
            if not candidato:
                break

            usuario = candidato
            break

        if not usuario:
            break

        AlocacaoEscala.objects.create(
            turno=turno,
            usuario=usuario,
            tipo="SOB",
            foi_acionado=False,
            data=data,  # 🔥 OBRIGATÓRIO AGORA
        )

        usados.add(usuario.id)

    return escala