from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from escalas.models import Escala

from .models import Pontuacao
from escalas.models import AlocacaoEscala
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def relatorio_secao(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    pontuacoes = (
        Pontuacao.objects
        .filter(usuario__secao=request.user.secao)
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
    
@login_required
def lancar_pontos(request, alocacao_id):
    if not request.user.pode_escalar():
        raise PermissionDenied

    alocacao = get_object_or_404(AlocacaoEscala, id=alocacao_id)

    escala = alocacao.turno.dia.escala
    if escala.secao != request.user.secao:
        raise PermissionDenied

    if request.method == "POST":
        pontos = int(request.POST.get("pontos"))

        # 🔥 tipo vem automaticamente do dia
        tipo_dia = alocacao.turno.dia.tipo_dia

        Pontuacao.objects.update_or_create(
            alocacao=alocacao,
            defaults={
                "usuario": alocacao.usuario,
                "pontos": pontos,
                "tipo": tipo_dia,
                "origem": Pontuacao.Origem.ESCALA,
            },
        )

        messages.success(request, "Pontuação registrada com sucesso.")
        return redirect("escalas:detalhe_escala", escala.id)

    return render(
        request,
        "pontuacao/lancar.html",
        {"alocacao": alocacao},
    )

# pontuacoes/views.py
@login_required
def painel_pontuacao(request):
    if not request.user.pode_escalar():
        raise PermissionDenied

    operadores = User.objects.filter(
        secao=request.user.secao,
        papel="OPE"
    ).order_by("first_name")

    return render(
        request,
        "pontuacao/painel.html",
        {"operadores": operadores},
    )

@login_required
def pontuar_operador(request, user_id):
    if not request.user.pode_escalar():
        raise PermissionDenied

    operador = get_object_or_404(User, id=user_id, papel="OPE")

    if operador.secao != request.user.secao:
        raise PermissionDenied

    if request.method == "POST":
        pontos = int(request.POST.get("pontos"))
        tipo = request.POST.get("tipo")
        observacao = request.POST.get("observacao", "")

        Pontuacao.objects.create(
            usuario=operador,
            pontos=pontos,
            tipo=tipo,
            observacao=observacao,
            origem=Pontuacao.Origem.MANUAL,
        )

        messages.success(request, "Pontuação lançada!")
        return redirect("pontuacao:operador", operador.id)

    historico = operador.pontuacoes.all()[:50]

    return render(
        request,
        "pontuacao/pontuar_operador.html",
        {
            "operador": operador,
            "historico": historico,
        },
    )