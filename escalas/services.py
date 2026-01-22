from datetime import timedelta
from django.db import transaction
from .models import Escala, DiaEscala, TurnoEscala, AlocacaoEscala
from .utils import SeletorOperadores, pode_assumir_turno
from django.db import transaction
from django.utils.timezone import now
from accounts.models import User
from django.db.models import Sum, Q, Count

from pontuacao.utils import registrar_pontuacao
from .models import Escala
from django.core.exceptions import ValidationError
from django.db.models import Sum

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

    colaboradores = (
        User.objects
        .filter(secao=secao, papel="OPE")
        .annotate(total_pontos=Sum("pontuacoes__pontos"))
        .order_by("total_pontos", "id")
    )

    seletor = SeletorOperadores(list(colaboradores))

    for i in range(7):
        data = data_inicio + timedelta(days=i)
        weekday = data.weekday()

        if weekday < 4:
            tipo_dia = "PRETA"
        elif weekday == 4:
            tipo_dia = "AMARELA"
        else:
            tipo_dia = "VERMELHA"

        dia = DiaEscala.objects.create(
            escala=escala,
            data=data,
            tipo_dia=tipo_dia,
        )

        if tipo_dia == "VERMELHA":
            continue

        usados_no_dia = set()

        for turno_codigo in TURNOS_PADRAO:
            turno = TurnoEscala.objects.create(
                dia=dia,
                turno=turno_codigo,
            )

            qtd = qtd_madrugada if turno_codigo == "MAD" else qtd_noturno

            # 🔹 TITULARES
            for _ in range(qtd):
                usuario = None

                for _ in range(len(seletor.operadores)):
                    candidato = seletor.proximo(data, usados_no_dia)
                    if not candidato:
                        break

                    if pode_assumir_turno(candidato, turno_codigo):
                        usuario = candidato
                        break

                if not usuario:
                    break

                AlocacaoEscala.objects.create(
                    turno=turno,
                    usuario=usuario,
                    tipo="TIT",
                )
                usados_no_dia.add(usuario.id)

            # 🔹 RESERVA
            usuario = None

            for _ in range(len(seletor.operadores)):
                candidato = seletor.proximo(data, usados_no_dia)
                if not candidato:
                    break

                if pode_assumir_turno(candidato, turno_codigo):
                    usuario = candidato
                    break

            if usuario:
                AlocacaoEscala.objects.create(
                    turno=turno,
                    usuario=usuario,
                    tipo="RES",
                )
                usados_no_dia.add(usuario.id)

    return escala



@transaction.atomic
def encerrar_escala(escala, usuario):
    if escala.status != Escala.Status.PUBLICADA:
        raise ValueError("A escala precisa estar publicada para ser encerrada.")

    if not usuario.pode_escalar():
        raise PermissionError("Usuário sem permissão.")

    for dia in escala.dias.all():
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

