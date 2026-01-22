# indisponibilidades/utils.py
from .models import Indisponibilidade

def usuario_disponivel(usuario, data):
    return not Indisponibilidade.objects.filter(
        usuario=usuario,
        data_inicio__lte=data,
        data_fim__gte=data,
    ).exists()
