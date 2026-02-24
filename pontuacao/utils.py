from .models import Pontuacao
from .services import calcular_pontos


def registrar_pontuacao(alocacao):
    """
    Cria ou atualiza pontuação baseada na alocação.
    Usado no encerramento da escala.
    """

    if not alocacao.usuario:
        return

    pontos = calcular_pontos(alocacao)

    if pontos == 0:
        return

    tipo = alocacao.turno.dia.tipo_dia

    Pontuacao.objects.update_or_create(
        alocacao=alocacao,
        defaults={
            "usuario": alocacao.usuario,
            "pontos": pontos,
            "tipo": tipo,
            "origem": Pontuacao.Origem.ESCALA,
        },
    )