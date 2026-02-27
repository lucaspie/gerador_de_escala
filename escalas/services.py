from datetime import timedelta
from django.db import transaction
from .models import Escala, DiaEscala, TurnoEscala, AlocacaoEscala
from .utils import SeletorOperadores, puxar_da_fila, fila_operadores, pontuar_alocacao
from django.db import transaction
from accounts.models import User
from django.db.models import Q, Count
from django.db.models import Prefetch
from escalas.ia.runtime import fila_operadores_com_ia
from .fairness import puxar_da_fila_fair
from collections import deque

from pontuacao.utils import registrar_pontuacao
from django.core.exceptions import ValidationError

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

@transaction.atomic
def gerar_escala_semanal(
    secao,
    data_inicio,
    criada_por,
    qtd_madrugada,
    qtd_noturno,
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
        Prefetch("turnos__alocacoes")
    )

    for dia in dias:
        for turno in dia.turnos.all():
            for alocacao in turno.alocacoes.all():
                registrar_pontuacao(alocacao)

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