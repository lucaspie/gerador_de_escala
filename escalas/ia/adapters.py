from collections import defaultdict
from escalas.models import AlocacaoEscala
from .domain import UsuarioEscala, Plantao


def carregar_historico_secao(secao):
    """
    Retorna lista de UsuarioEscala com histórico completo.
    """

    alocacoes = (
        AlocacaoEscala.objects
        .select_related("usuario", "turno__dia")
        .filter(usuario__secao=secao, usuario__is_active=True)
    )

    mapa = defaultdict(list)

    for a in alocacoes:
        if not a.usuario:
            continue

        data = a.turno.dia.data
        turno = a.turno.turno  # MAD, NOT, SOB

        # sobreaviso acionado
        if turno == "SOB" and a.foi_acionado:
            tipo = "SOB_ATIVO"
        else:
            tipo = turno

        mapa[a.usuario].append(Plantao(data=data, tipo=tipo))

    usuarios = []
    for user, plantoes in mapa.items():
        usuarios.append(
            UsuarioEscala(
                user_id=user.id,
                nome=user.get_full_name() or user.username,
                plantoes=plantoes,
            )
        )

    return usuarios