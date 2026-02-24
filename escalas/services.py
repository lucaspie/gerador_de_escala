from datetime import timedelta
from django.db import transaction
from .models import Escala, DiaEscala, TurnoEscala, AlocacaoEscala
from .utils import SeletorOperadores, puxar_da_fila, fila_operadores, pontuar_alocacao
from django.db import transaction
from accounts.models import User
from django.db.models import Q, Count
from django.db.models import Prefetch

from pontuacao.utils import registrar_pontuacao
from django.core.exceptions import ValidationError

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

    fila = fila_operadores(secao)

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
    # 2️⃣ TITULARES AMARELA
    # =========================
    for data, turno_codigo, turno in amarelos:
        usados_no_dia = set()

        qtd = qtd_madrugada if turno_codigo == "MAD" else qtd_noturno

        for _ in range(qtd):
            op = puxar_da_fila(fila, data, turno_codigo, usados_no_dia)
            if not op:
                break

            aloc = AlocacaoEscala.objects.create(
                turno=turno,
                usuario=op,
                tipo="TIT",
            )
            usados_no_dia.add(op.id)
            pontuar_alocacao(aloc)

    # =========================
    # 3️⃣ TITULARES PRETA
    # =========================
    for data, turno_codigo, turno in pretos:
        usados_no_dia = set()

        qtd = qtd_madrugada if turno_codigo == "MAD" else qtd_noturno

        for _ in range(qtd):
            op = puxar_da_fila(fila, data, turno_codigo, usados_no_dia)
            if not op:
                break

            aloc = AlocacaoEscala.objects.create(
                turno=turno,
                usuario=op,
                tipo="TIT",
            )
            usados_no_dia.add(op.id)
            pontuar_alocacao(aloc)

    # =========================
    # 4️⃣ RESERVAS (TUDO)
    # =========================
    todos = amarelos + pretos

    for data, turno_codigo, turno in todos:
        usados_no_dia = set(
            AlocacaoEscala.objects.filter(
                turno__dia__data=data
            ).values_list("usuario_id", flat=True)
        )

        op = puxar_da_fila(fila, data, turno_codigo, usados_no_dia)

        if op:
            AlocacaoEscala.objects.create(
                turno=turno,
                usuario=op,
                tipo="RES",
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

        # 🔁 tenta vários candidatos
        for _ in range(len(operadores)):
            candidato = seletor.proximo(data, usados)
            if not candidato:
                break

            # futuramente: regra específica
            # if not pode_assumir_sobreaviso(candidato):
            #     continue

            usuario = candidato
            break

        if not usuario:
            break

        AlocacaoEscala.objects.create(
            turno=turno,
            usuario=usuario,
            tipo="SOB",
            foi_acionado=False,
        )

        usados.add(usuario.id)

    return escala

