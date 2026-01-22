from .models import Pontuacao
from .services import calcular_pontos


def registrar_pontuacao(alocacao):
    pontos = calcular_pontos(alocacao)

    Pontuacao.objects.create(
        usuario=alocacao.usuario,
        alocacao=alocacao,
        pontos=pontos,
    )
