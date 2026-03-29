# indisponibilidades/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Indisponibilidade
from .forms import IndisponibilidadeForm

@login_required
def minhas_indisponibilidades(request):
    hoje = timezone.now().date()
    inicio_janela = hoje - timedelta(days=10)
    fim_janela = hoje + timedelta(days=10)

    base_qs = Indisponibilidade.objects.filter(
        usuario=request.user
    )

    proximas = base_qs.filter(
        data_inicio__lte=fim_janela,
        data_fim__gte=inicio_janela,
    ).order_by("data_inicio")

    todas = base_qs.order_by("status", "-data_inicio")

    return render(
        request,
        "indisponibilidades/minhas_indisponibilidades.html",
        {
            "proximas": proximas,
            "todas": todas,
        },
    )

@login_required
def criar_indisponibilidade(request):
    if request.method == "POST":
        form = IndisponibilidadeForm(request.POST, usuario=request.user)
        if form.is_valid():
            indisp = form.save(commit=False)
            indisp.usuario = request.user
            indisp.save()
            messages.success(request, "Indisponibilidade registrada.")
            return redirect("indisponibilidades:minhas")
    else:
        form = IndisponibilidadeForm()

    return render(
        request,
        "indisponibilidades/criar_indisponibilidade.html",
        {"form": form},
    )

@login_required
def excluir_indisponibilidade(request, pk):
    indisp = get_object_or_404(
        Indisponibilidade,
        pk=pk,
        usuario=request.user,
    )

    if request.method == "POST":
        indisp.delete()
        messages.success(request, "Indisponibilidade removida.")
        return redirect("indisponibilidades:minhas")

    return render(
        request,
        "indisponibilidades/confirmar_exclusao.html",
        {"indisponibilidade": indisp},
    )

from django.utils import timezone
from datetime import timedelta

@login_required
def indisponibilidades_secao(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    hoje = timezone.now().date()
    inicio_janela = hoje - timedelta(days=10)
    fim_janela = hoje + timedelta(days=10)

    base_qs = Indisponibilidade.objects.filter(
        usuario__secao=request.user.secao
    ).select_related("usuario")

    # 📌 Janela prioritária
    proximas = base_qs.filter(
        data_inicio__lte=fim_janela,
        data_fim__gte=inicio_janela,
    ).order_by("data_inicio")

    # 📚 Todas
    todas = base_qs.order_by("status","-data_inicio")

    return render(
        request,
        "indisponibilidades/lista_secao.html",
        {
            "proximas": proximas,
            "todas": todas,
        },
    )

@login_required
@require_POST
def aprovar_indisponibilidade(request, pk):
    if not request.user.pode_escalar():
        raise PermissionDenied

    indisp = get_object_or_404(Indisponibilidade, pk=pk)

    # 🔒 Segurança: só da mesma seção
    if indisp.usuario.secao != request.user.secao:
        raise PermissionDenied

    indisp.status = Indisponibilidade.Status.APROVADA
    indisp.save(update_fields=["status"])

    messages.success(request, "Indisponibilidade aprovada.")
    return redirect(request.META.get("HTTP_REFERER", "indisponibilidades:secao"))

@login_required
@require_POST
def recusar_indisponibilidade(request, pk):
    if not request.user.pode_escalar():
        raise PermissionDenied

    indisp = get_object_or_404(Indisponibilidade, pk=pk)

    if indisp.usuario.secao != request.user.secao:
        raise PermissionDenied

    indisp.status = Indisponibilidade.Status.RECUSADA
    indisp.save(update_fields=["status"])

    messages.warning(request, "Indisponibilidade recusada.")
    return redirect(request.META.get("HTTP_REFERER", "indisponibilidades:secao"))