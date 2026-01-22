from indisponibilidades.models import Indisponibilidade

def usuario_disponivel(usuario, data):
    return not Indisponibilidade.objects.filter(
        usuario=usuario,
        data_inicio__lte=data,
        data_fim__gte=data,
    ).exists()

def pode_assumir_turno(usuario, turno_codigo):
    """
    Retorna True se o usuário pode operar o turno informado
    considerando seus cursos.
    """

    cursos = set(
        usuario.cursos.values_list("codigo", flat=True)
    )

    tem_pista = "PIS" in cursos
    tem_manutencao = "MAN" in cursos

    if turno_codigo == "MAD":
        return tem_pista

    if turno_codigo == "NOT":
        return tem_manutencao

    return False

class SeletorOperadores:
    def __init__(self, operadores):
        self.operadores = operadores
        self.indice = 0
        self.total = len(operadores)

    def proximo(self, data, ignorar_ids=None):
        ignorar_ids = ignorar_ids or set()
        tentativas = 0
        while tentativas < self.total:
            usuario = self.operadores[self.indice % self.total]
            self.indice += 1
            tentativas += 1

            if usuario.id in ignorar_ids:
                continue

            if not usuario_disponivel(usuario, data):
                continue
            return usuario
        return None