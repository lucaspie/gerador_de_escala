from datetime import timedelta
from indisponibilidades.models import Indisponibilidade

def montar_mapa_indisponibilidade(secao, dias):
    # 1. Garante que tudo vira 'date' puro logo na entrada
    datas = []
    for d in dias:
        obj = d.data if hasattr(d, "data") else d
        # Se for datetime, extrai apenas a data. Se for date, mantém.
        datas.append(obj.date() if hasattr(obj, "date") else obj)

    if not datas:
        return set()

    # 2. Busca otimizada no banco
    indisps = Indisponibilidade.objects.filter(
        usuario__secao=secao,
        data_inicio__lte=max(datas),
        data_fim__gte=min(datas),
    )

    mapa = set()

    # 3. Preenchimento do set com garantia de tipo date puro
    for ind in indisps:
        # Extrai .date() caso o campo no banco seja DateTimeField
        inicio = ind.data_inicio.date() if hasattr(ind.data_inicio, "date") else ind.data_inicio
        fim = ind.data_fim.date() if hasattr(ind.data_fim, "date") else ind.data_fim
        
        atual = inicio
        while atual <= fim:
            mapa.add((ind.usuario_id, atual))
            atual += timedelta(days=1)

    return mapa