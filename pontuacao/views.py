from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .models import Pontuacao


@login_required
def relatorio_secao(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    pontuacoes = (
        Pontuacao.objects
        .filter(alocacao__turno__dia__escala__secao=request.user.secao)
        .values(
            "usuario__id",
            "usuario__first_name",
            "usuario__username",
            "usuario__last_name",
        )
        .annotate(total=Sum("pontos"))
        .order_by("-total")
    )

    return render(
        request,
        "pontuacao/relatorio_secao.html",
        {"pontuacoes": pontuacoes},
    )

@login_required
def minha_pontuacao(request):
    pontuacoes = (
        Pontuacao.objects
        .filter(usuario=request.user)
        .select_related(
            "alocacao__turno__dia__escala"
        )
    )

    total = pontuacoes.aggregate(
        total=Sum("pontos")
    )["total"] or 0

    return render(
        request,
        "pontuacao/minha_pontuacao.html",
        {
            "pontuacoes": pontuacoes,
            "total": total,
        },
    )