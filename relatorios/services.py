from django.db.models import Sum
from pontuacao.models import Pontuacao


def pontuacao_por_secao(secao, data_inicio=None, data_fim=None):
    qs = Pontuacao.objects.filter(
        alocacao__turno__dia__escala__secao=secao
    )

    if data_inicio and data_fim:
        qs = qs.filter(
            criado_em__date__range=(data_inicio, data_fim)
        )

    return (
        qs.values("usuario__username")
        .annotate(total=Sum("pontos"))
        .order_by("-total")
    )
