from django.db.models import Sum, Q
from pontuacao.models import Pontuacao


def pontuacao_por_secao(secao, data_inicio=None, data_fim=None):
    qs = Pontuacao.objects.filter(
        usuario__secao=secao
    )

    if data_inicio and data_fim:
        qs = qs.filter(
            criado_em__date__range=(data_inicio, data_fim)
        )

    return (
        qs.values("usuario__username")
        .annotate(
            total=Sum("pontos"),

            preta=Sum(
                "pontos",
                filter=Q(tipo=Pontuacao.Tipo.PRETA)
            ),

            amarela=Sum(
                "pontos",
                filter=Q(tipo=Pontuacao.Tipo.AMARELA)
            ),

            vermelha=Sum(
                "pontos",
                filter=Q(tipo=Pontuacao.Tipo.VERMELHA)
            ),
        )
        .order_by("-total")
    )