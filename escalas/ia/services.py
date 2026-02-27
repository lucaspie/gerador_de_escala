from .adapters import carregar_historico_secao
from .engine import MotorEscalaIA
from indisponibilidades.models import Indisponibilidade

def filtrar_indisponiveis(usuarios, data_turno):
    """
    Remove usuários que possuem indisponibilidade ativa na data.
    """

    from django.contrib.auth import get_user_model
    User = get_user_model()

    users_ids = [u.user_id for u in usuarios]

    indisponiveis_ids = (
        Indisponibilidade.objects
        .filter(
            usuario_id__in=users_ids,
            data_inicio__lte=data_turno,
            data_fim__gte=data_turno,
        )
        .values_list("usuario_id", flat=True)
    )

    indisponiveis_ids = set(indisponiveis_ids)

    return [u for u in usuarios if u.user_id not in indisponiveis_ids]

def sugerir_operador(secao, data_turno, debug=False):
    usuarios = carregar_historico_secao(secao)

    if not usuarios:
        return None

    # 🔥 FILTRO DE INDISPONIBILIDADE
    usuarios_filtrados = filtrar_indisponiveis(usuarios, data_turno)

    if not usuarios_filtrados:
        return None

    motor = MotorEscalaIA(usuarios_filtrados)
    escolhido = motor.escolher(debug=debug)

    return escolhido.user_id