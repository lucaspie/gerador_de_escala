# indisponibilidades/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from .models import Indisponibilidade
from .forms import IndisponibilidadeForm

@login_required
def minhas_indisponibilidades(request):
    indisps = Indisponibilidade.objects.filter(
        usuario=request.user
    )

    return render(
        request,
        "indisponibilidades/minhas_indisponibilidades.html",
        {"indisponibilidades": indisps},
    )

@login_required
def criar_indisponibilidade(request):
    if request.method == "POST":
        form = IndisponibilidadeForm(request.POST)
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

@login_required
def indisponibilidades_secao(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    indisps = Indisponibilidade.objects.filter(
        usuario__secao=request.user.secao
    ).select_related("usuario")

    return render(
        request,
        "indisponibilidades/lista_secao.html",
        {"indisponibilidades": indisps},
    )
