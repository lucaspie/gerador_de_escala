from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .models import Escala
from .services import gerar_escala_semanal, encerrar_escala, acionar_sobreaviso, criar_sobreaviso_service
from .forms import CriarEscalaForm
from django.contrib import messages
from django.db import transaction
from .models import TurnoEscala, AlocacaoEscala, DiaEscala, User
from django.utils.timezone import now
from django.db.models import Prefetch

@login_required
def criar_escala(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    if request.method == "POST":
        form = CriarEscalaForm(request.POST)
        if form.is_valid():
            escala = gerar_escala_semanal(
                secao=request.user.secao,
                data_inicio=form.cleaned_data["data_inicio"],
                criada_por=request.user,
                # ↓ ainda não usamos, mas já preparamos
                qtd_madrugada=form.cleaned_data["qtd_madrugada"],
                qtd_noturno=form.cleaned_data["qtd_noturno"],
            )
            return redirect("escalas:detalhe_escala", escala.id)
    else:
        form = CriarEscalaForm()

    return render(
        request,
        "escalas/criar_escala.html",
        {"form": form},
    )

@login_required
def detalhe_escala(request, escala_id):
    escala = get_object_or_404(Escala, id=escala_id)

    if escala.secao != request.user.secao:
        raise PermissionDenied

    pode_editar = (
        request.user.pode_escalar()
        and escala.status == Escala.Status.RASCUNHO
    )

    return render(
        request,
        "escalas/detalhe_escala.html",
        {
            "escala": escala,
            "pode_editar": pode_editar,
        },
    )

@login_required
def publicar_escala(request, escala_id):
    escala = get_object_or_404(Escala, id=escala_id)

    if not request.user.pode_escalar():
        raise PermissionDenied

    escala.status = Escala.Status.PUBLICADA
    escala.save()

    return redirect("escalas:detalhe_escala", escala.id)

@login_required
def encerrar_escala_view(request, escala_id):
    escala = get_object_or_404(Escala, id=escala_id)

    encerrar_escala(escala, request.user)

    return redirect("escalas:detalhe_escala", escala.id)

@login_required
def editar_turno(request, turno_id):
    turno = get_object_or_404(TurnoEscala, id=turno_id)

    escala = turno.dia.escala

    if escala.secao != request.user.secao:
        raise PermissionDenied

    if not request.user.pode_escalar():
        raise PermissionDenied

    if escala.status != Escala.Status.RASCUNHO:
        raise PermissionDenied("Escala não pode mais ser editada.")

    operadores = User.objects.filter(
        secao=escala.secao,
        papel="OPE"
    )

    if request.method == "POST":
        with transaction.atomic():
            turno.alocacoes.all().delete()

            titulares_ids = request.POST.getlist("titulares")
            reserva_id = request.POST.get("reserva")
            substituido_usuario_id = request.POST.get("substituido")  # USER id

            alocacoes_titulares = {}

            # TITULARES
            for user_id in titulares_ids:
                aloc = AlocacaoEscala.objects.create(
                    turno=turno,
                    usuario_id=user_id,
                    tipo="TIT",
                )
                alocacoes_titulares[user_id] = aloc

            # RESERVA
            if reserva_id:
                reserva = AlocacaoEscala.objects.create(
                    turno=turno,
                    usuario_id=reserva_id,
                    tipo="RES",
                    foi_acionado=True,
                )

                # SE HOUVE SUBSTITUIÇÃO
                if substituido_usuario_id:
                    titular_substituido = alocacoes_titulares.get(substituido_usuario_id)
                    if titular_substituido:
                        reserva.substituiu = titular_substituido
                        reserva.save()

        messages.success(request, "Turno atualizado com sucesso.")
        return redirect("escalas:detalhe_escala", escala.id)

    return render(
        request,
        "escalas/editar_turno.html",
        {
            "turno": turno,
            "operadores": operadores,
            "escala": escala,
        },
    )

@login_required
def lista_escalas(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    escalas = Escala.objects.filter(
        secao=request.user.secao
    ).order_by("-data_inicio")

    return render(
        request,
        "escalas/lista_escalas.html",
        {
            "escalas": escalas,
        },
    )

@login_required
def semanas_escalante(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    hoje = date.today()

    # Segunda-feira da semana atual
    inicio_semana = hoje - timedelta(days=hoje.weekday())

    # Vamos mostrar, por exemplo, 8 semanas (4 passadas + atual + 3 futuras)
    semanas = []
    for i in range(-4, 4):
        semana_inicio = inicio_semana + timedelta(weeks=i)
        semana_fim = semana_inicio + timedelta(days=6)

        escala = Escala.objects.filter(
            secao=request.user.secao,
            data_inicio=semana_inicio,
        ).first()

        semanas.append({
            "inicio": semana_inicio,
            "fim": semana_fim,
            "escala": escala,
        })

    return render(
        request,
        "escalas/semanas.html",
        {
            "semanas": semanas,
        },
    )

@login_required
def apagar_escala(request, escala_id):
    escala = get_object_or_404(Escala, id=escala_id)

    if escala.secao != request.user.secao:
        raise PermissionDenied

    if not request.user.pode_escalar():
        raise PermissionDenied

    if escala.status != Escala.Status.RASCUNHO:
        messages.error(
            request,
            "Apenas escalas em rascunho podem ser apagadas."
        )
        return redirect("escalas:detalhe_escala", escala.id)

    if request.method == "POST":
        with transaction.atomic():
            escala.delete()

        messages.success(
            request,
            "Escala apagada com sucesso."
        )
        return redirect("escalas:semanas_escalante")

    return render(
        request,
        "escalas/confirmar_apagar.html",
        {
            "escala": escala,
        },
    )

@login_required
def minhas_escalas(request):
    if request.user.papel != "OPE":
        raise PermissionDenied

    escalas = (
        Escala.objects
        .filter(
            secao=request.user.secao,
            status=Escala.Status.PUBLICADA,
            dias__turnos__alocacoes__usuario=request.user
        )
        .distinct()
        .prefetch_related(
            Prefetch(
                "dias",
                queryset=DiaEscala.objects.prefetch_related(
                    "turnos__alocacoes"
                )
            )
        )
        .order_by("-data_inicio")
    )

    return render(
        request,
        "escalas/minhas_escalas.html",
        {
            "escalas": escalas,
        },
    )

@login_required
def acionar_sobreaviso_view(request, alocacao_id):
    alocacao = get_object_or_404(AlocacaoEscala, id=alocacao_id)

    escala = alocacao.turno.dia.escala

    if escala.secao != request.user.secao:
        raise PermissionDenied

    if not request.user.pode_escalar():
        raise PermissionDenied

    if escala.status != Escala.Status.PUBLICADA:
        messages.error(
            request,
            "Só é possível acionar sobreaviso em escala publicada."
        )
        return redirect("escalas:detalhe_escala", escala.id)

    try:
        acionar_sobreaviso(alocacao)
        messages.success(
            request,
            f"{alocacao.usuario.username} foi marcado como ACIONADO."
        )
    except Exception as e:
        messages.error(request, str(e))

    return redirect("escalas:detalhe_escala", escala.id)

@login_required
def criar_sobreaviso_view(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    if request.method == "POST":
        data = request.POST.get("data")
        quantidade = int(request.POST.get("quantidade"))

        criar_sobreaviso_service(
            secao=request.user.secao,
            data=data,
            quantidade=quantidade,
            criada_por=request.user,
        )

        messages.success(
            request,
            "Sobreaviso criado com sucesso."
        )
        return redirect("accounts:dashboard")

    return render(
        request,
        "escalas/criar_sobreaviso.html",
    )

@login_required
def acionar_sobreaviso(request, alocacao_id):
    if not request.user.pode_escalar():
        raise PermissionDenied

    alocacao = get_object_or_404(
        AlocacaoEscala,
        id=alocacao_id,
        tipo="SOB",
    )

    if request.method == "POST":
        alocacao.foi_acionado = True
        alocacao.save()

        messages.success(
            request,
            f"Sobreaviso de {alocacao.usuario.username} acionado com sucesso."
        )

        return redirect("escalas:detalhe_escala", alocacao.turno.dia.escala.id)

    return render(
        request,
        "escalas/acionar_sobreaviso.html",
        {"alocacao": alocacao},
    )

@login_required
def acionar_reserva(request, alocacao_id):
    alocacao = get_object_or_404(
        AlocacaoEscala,
        id=alocacao_id,
        tipo="RES",
    )

    escala = alocacao.turno.dia.escala

    if escala.secao != request.user.secao:
        raise PermissionDenied

    if not request.user.pode_escalar():
        raise PermissionDenied

    if escala.status != Escala.Status.PUBLICADA:
        messages.error(
            request,
            "A escala precisa estar publicada."
        )
        return redirect("escalas:detalhe_escala", escala.id)

    titulares = alocacao.turno.alocacoes.filter(tipo="TIT")

    if request.method == "POST":
        substituido_id = request.POST.get("substituido")

        with transaction.atomic():
            alocacao.foi_acionado = True

            if substituido_id:
                titular = get_object_or_404(
                    AlocacaoEscala,
                    id=substituido_id,
                    tipo="TIT",
                )
                alocacao.substituiu = titular
                alocacao.virou_titular = True

            alocacao.save()

        messages.success(
            request,
            "Reserva acionado com sucesso."
        )

        return redirect(
            "escalas:detalhe_escala",
            escala.id
        )

    return render(
        request,
        "escalas/acionar_reserva.html",
        {
            "alocacao": alocacao,
            "titulares": titulares,
            "escala": escala,
        },
    )
