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
    
from .models import Pontuacao
from .services import calcular_pontos


def registrar_pontuacoes_em_lote(alocacoes):
    pontuacoes_para_criar = []
    pontuacoes_para_atualizar = []

    # Buscar existentes de uma vez
    existentes = {
        p.alocacao_id: p
        for p in Pontuacao.objects.filter(alocacao__in=alocacoes)
    }

    for alocacao in alocacoes:
        if not alocacao.usuario:
            continue

        pontos = calcular_pontos(alocacao)
        if pontos == 0:
            continue

        tipo = alocacao.turno.dia.tipo_dia

        if alocacao.id in existentes:
            p = existentes[alocacao.id]
            p.usuario = alocacao.usuario
            p.pontos = pontos
            p.tipo = tipo
            p.origem = Pontuacao.Origem.ESCALA
            pontuacoes_para_atualizar.append(p)
        else:
            pontuacoes_para_criar.append(
                Pontuacao(
                    alocacao=alocacao,
                    usuario=alocacao.usuario,
                    pontos=pontos,
                    tipo=tipo,
                    origem=Pontuacao.Origem.ESCALA,
                )
            )

    # Executa em lote
    if pontuacoes_para_criar:
        Pontuacao.objects.bulk_create(pontuacoes_para_criar)

    if pontuacoes_para_atualizar:
        Pontuacao.objects.bulk_update(
            pontuacoes_para_atualizar,
            ["usuario", "pontos", "tipo", "origem"],
        )