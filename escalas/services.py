from datetime import timedelta
from django.db import transaction
from .models import Escala, DiaEscala, TurnoEscala, AlocacaoEscala
from .utils import SeletorOperadores, fila_operadores_balanceada, pontuar_alocacao
from django.db import transaction
from accounts.models import User
from django.db.models import Q, Count
from django.db.models import Prefetch
from escalas.ia.runtime import fila_operadores_com_ia
from .fairness import puxar_da_fila_fair, calcular_stats, pode_assumir_turno, usuario_disponivel
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
    fila = fila_operadores_balanceada(secao)

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

def calcular_participacao_semanal(secao, semanas=8):
    from django.utils import timezone
    from datetime import timedelta

    inicio = timezone.now().date() - timedelta(days=7 * semanas)

    participacoes = (
        AlocacaoEscala.objects
        .filter(
            turno__dia__escala__secao=secao,
            turno__dia__data__gte=inicio,
            tipo="TIT"
        )
        .values("usuario", "turno__dia__escala")
        .distinct()
    )

    contador = {}

    for item in participacoes:
        user = item["usuario"]
        contador[user] = contador.get(user, 0) + 1

    return contador

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

def alocar_turno(
    turno,
    data,
    qtd,
    fila,
    usados_no_dia,
    secao,
    stats,
    tipo="TIT"
):
    alocados = []

    from django.db import IntegrityError

    for _ in range(qtd):
        op = None

        # 🔁 tenta achar alguém válido
        for _ in range(len(fila)):
            candidato = puxar_da_fila_fair(
                fila, data, turno, usados_no_dia, secao, stats=stats
            )

            if not candidato:
                break

            # 🚫 JÁ FOI USADO → ignora
            if candidato.id in usados_no_dia:
                continue

            op = candidato
            break

        if not op:
            break

        try:
            aloc = AlocacaoEscala.objects.create(
                turno=turno,
                usuario=op,
                tipo=tipo,
                data=data,
            )

            usados_no_dia.add(op.id)

            if tipo == "TIT":
                pontuar_alocacao(aloc)

            alocados.append(op)

        except IntegrityError:
            # 🛡️ proteção extra contra concorrência
            continue

    return alocados

def gerar_escala_semanal_fixa(
    dias,
    secao,
    qtd_operadores_semana,
    qtd_madrugada,
    qtd_noturno,
    usar_reserva=True
):
    # =========================
    # 1️⃣ Seleciona grupo fixo
    # =========================
    
    stats = calcular_stats(secao, dias=365)

    operadores = list(
        User.objects.filter(secao=secao, papel="OPE")
    )

    def score(op):
        dados = stats.get(op.id, {"total": 0, "preta": 0, "amarela": 0})
        return (
            dados["total"] * 10 +
            dados["preta"] * 3 +
            dados["amarela"] * 2
        )

    operadores.sort(key=lambda op: (score(op), op.id))

    # 🔥 GRUPO FIXO DA SEMANA
    operadores_semana = operadores[:qtd_operadores_semana]

    # 🔥 RESTO = fallback
    fila_fallback = deque(operadores[qtd_operadores_semana:])

    # =========================
    # 2️⃣ LOOP DOS DIAS
    # =========================
    for dia in dias:
        if dia.tipo_dia == "VERMELHA":
            continue

        usados_no_dia = set()

        for turno in dia.turnos.all():

            qtd = qtd_madrugada if turno.turno == "MAD" else qtd_noturno

            if qtd == 0:
                continue

            # =========================
            # 3️⃣ TITULARES FIXOS
            # =========================
            candidatos_fixos = [
                op for op in operadores_semana
                if op.id not in usados_no_dia
                and usuario_disponivel(op, dia.data)
                and not (turno.turno == "MAD" and not pode_assumir_turno(op, "MAD"))
                and not (turno.turno == "NOT" and not pode_assumir_turno(op, "NOT"))
            ]

            # 🔥 pega os primeiros disponíveis
            selecionados = candidatos_fixos[:qtd]

            # =========================
            # 🔁 COMPLETA COM FALLBACK
            # =========================
            while len(selecionados) < qtd:
                op = puxar_da_fila_fair(
                    fila_fallback,
                    dia.data,
                    turno,
                    usados_no_dia,
                    secao,
                    stats=stats
                )

                if not op:
                    break

                selecionados.append(op)

            # =========================
            # 💾 SALVAR TITULARES
            # =========================
            for op in selecionados:
                usados_no_dia.add(op.id)

                aloc = AlocacaoEscala.objects.create(
                    turno=turno,
                    usuario=op,
                    tipo="TIT",
                    data=dia.data,
                )

                pontuar_alocacao(aloc)

            # =========================
            # 4️⃣ RESERVA (opcional)
            # =========================
            if usar_reserva:

                op = puxar_da_fila_fair(
                    fila_fallback,
                    dia.data,
                    turno,
                    usados_no_dia,
                    secao,
                    stats=stats
                )

                if op:
                    usados_no_dia.add(op.id)

                    AlocacaoEscala.objects.create(
                        turno=turno,
                        usuario=op,
                        tipo="RES",
                        data=dia.data,
                    )

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

    fila = fila_operadores_balanceada(secao)
    stats = calcular_stats(secao)

    dias_processados = []

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

            dias_processados.append((data, turno_codigo, turno))

    # =========================
    # MODO FIXO
    # =========================
    if modo == "SEM":
        dias = escala.dias.prefetch_related("turnos__alocacoes")

        gerar_escala_semanal_fixa(
            dias,
            secao,
            qtd_operadores_semana=6,
            qtd_madrugada=qtd_madrugada,
            qtd_noturno=qtd_noturno,
            usar_reserva=True
        )
        return escala

    # =========================
    # 2️⃣ ALOCAÇÃO PRINCIPAL
    # =========================
    usados_global = {}

    for data, turno_codigo, turno in dias_processados:

        usados_no_dia = usados_global.setdefault(data, set())

        qtd = qtd_madrugada if turno_codigo == "MAD" else qtd_noturno

        if qtd == 0:
            continue

        alocar_turno(
            turno=turno,
            data=data,
            qtd=qtd,
            fila=fila,
            usados_no_dia=usados_no_dia,
            secao=secao,
            stats=stats,
            tipo="TIT"
        )

    # =========================
    # 3️⃣ VALIDAR NOT
    # =========================
    for data, turno_codigo, turno in dias_processados:
        if turno_codigo != "NOT" or qtd_noturno == 0:
            continue

        if not turno.alocacoes.filter(
            usuario__cursos__codigo="MAN",
            tipo="TIT"
        ).exists():
            raise ValidationError(
                f"Turno noturno do dia {data} ficou sem habilitado."
            )

    # =========================
    # 4️⃣ RESERVAS
    # =========================
    for data, turno_codigo, turno in dias_processados:

        usados_no_dia = usados_global.setdefault(data, set())

        alocar_turno(
            turno=turno,
            data=data,
            qtd=1,
            fila=fila,
            usados_no_dia=usados_no_dia,
            secao=secao,
            stats=stats,
            tipo="RES"
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