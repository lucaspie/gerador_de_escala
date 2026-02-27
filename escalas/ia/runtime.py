from collections import deque
from accounts.models import User
from django.db.models import Sum, Count, Q, F, FloatField, ExpressionWrapper
from escalas.ia.simulador import OperadorIA
from escalas.ia.autoajuste import ParametrosIA
from django.conf import settings

def carregar_parametros_ia():
    """
    Carrega IA treinada do settings ou fallback padrão
    """
    data = getattr(settings, "ESCALA_IA_PARAMS", None)

    if not data:
        return ParametrosIA()

    return ParametrosIA(**data)

def fila_operadores_com_ia(secao):
    params = carregar_parametros_ia()

    users = User.objects.filter(secao=secao, papel="OPE")

    operadores = []

    for u in users:
        op = OperadorIA(u)

        # puxar stats reais
        stats = u.pontuacoes.aggregate(
            pontos=Sum("pontos"),
            amarelas=Count("id", filter=Q(tipo="AMARELA")),
        )

        op.pontos = stats["pontos"] or 0
        op.amarelas = stats["amarelas"] or 0

        operadores.append(op)

    # ordenar com IA
    operadores.sort(
        key=lambda op: (
            op.pontos * params.peso_pontos +
            op.amarelas * params.peso_amarelas +
            op.sobreavisos * params.peso_sobreaviso
        )
    )

    # converter para Users novamente
    ordered_ids = [op.id for op in operadores]
    mapa = {u.id: u for u in users}

    return deque([mapa[i] for i in ordered_ids])