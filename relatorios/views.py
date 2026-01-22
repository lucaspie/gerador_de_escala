from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from datetime import date, timedelta
from django.db.models import Sum, Count, Q

from .services import pontuacao_por_secao
from .exports import exportar_pontuacao_excel
from indisponibilidades.models import Indisponibilidade
from escalas.models import AlocacaoEscala

@login_required
def relatorio_pontuacao_secao(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    # ===============================
    # 1️⃣ PONTUAÇÃO GERAL
    # ===============================
    dados = pontuacao_por_secao(
        secao=request.user.secao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    labels = [d["usuario__username"] for d in dados]
    valores = [float(d["total"]) for d in dados]

    # ===============================
    # 2️⃣ SOBREAVISO (DIAS VERMELHOS)
    # ===============================
    sobreavisos = (
        AlocacaoEscala.objects
        .filter(
            turno__dia__escala__secao=request.user.secao,
            tipo="SOB",
        )
    )

    if data_inicio:
        sobreavisos = sobreavisos.filter(
            turno__dia__data__gte=data_inicio
        )

    if data_fim:
        sobreavisos = sobreavisos.filter(
            turno__dia__data__lte=data_fim
        )

    sobreavisos = (
        sobreavisos
        .values("usuario__username")
        .annotate(
            total_sobreavisos=Count("id"),
            acionamentos=Count(
                "id",
                filter=Q(foi_acionado=True),
            ),
            pontos=Sum("pontuacoes__pontos", default=0),
        )
        .order_by("-pontos").filter(
            turno__dia__escala__secao=request.user.secao,
            tipo="SOB",
        )

    )

    return render(
        request,
        "relatorios/pontuacao_secao.html",
        {
            "dados": dados,
            "labels": labels,
            "valores": valores,
            "sobreavisos": sobreavisos,  # 👈 NOVO
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    )

@login_required
def exportar_excel(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    return exportar_pontuacao_excel(
        secao=request.user.secao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

from .exports import exportar_pontuacao_pdf


@login_required
def exportar_pdf(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    return exportar_pontuacao_pdf(
        secao=request.user.secao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

@login_required
def dashboard(request):
    hoje = date.today()
    limite = hoje + timedelta(days=30)  # próximos 30 dias

    indisponibilidades = []

    if request.user.pode_escalar():
        indisponibilidades = (
            Indisponibilidade.objects
            .filter(
                usuario__secao=request.user.secao,
                data_fim__gte=hoje,
                data_inicio__lte=limite,
            )
            .select_related("usuario")
            .order_by("data_inicio")
        )

    return render(
        request,
        "dashboard.html",
        {
            "indisponibilidades": indisponibilidades,
        },
    )