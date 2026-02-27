from indisponibilidades.models import Indisponibilidade
from django.db.models import Sum, Q, Value, Count
from accounts.models import User
from collections import defaultdict
from collections import deque
from pontuacao.models import Pontuacao
from django.db.models import F, ExpressionWrapper, FloatField
from accounts.models import Curso

def pontuar_alocacao(alocacao):
    tipo_dia = alocacao.turno.dia.tipo_dia

    mapa_tipo = {
        "PRETA": Pontuacao.Tipo.PRETA,
        "AMARELA": Pontuacao.Tipo.AMARELA,
        "VERMELHA": Pontuacao.Tipo.VERMELHA,
    }

    # você pode ajustar pesos aqui
    pesos = {
        "PRETA": 1,
        "AMARELA": 2,  # sexta vale mais
        "VERMELHA": 3,
    }

    tipo = mapa_tipo.get(tipo_dia)
    pontos = pesos.get(tipo_dia, 0)

    if alocacao.tipo != "TIT":
        return  # reserva não pontua

    Pontuacao.objects.create(
        usuario=alocacao.usuario,
        alocacao=alocacao,
        tipo=tipo,
        origem=Pontuacao.Origem.ESCALA,
        pontos=pontos,
    )

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
    def __init__(self, operadores, start_index=0):
        self.operadores = operadores
        self.indice = start_index
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

def operadores_ordenados(secao):
    return list(
        User.objects
        .filter(secao=secao, papel="OPE")
        .annotate(total_pontos=Sum("pontuacoes__pontos"))
        .order_by("total_pontos", "id")
    )
    
def fila_operadores(secao):
    operadores = (
        User.objects
        .filter(secao=secao, papel="OPE")
        .annotate(
            total_pontos=Sum("pontuacoes__pontos"),
            total_amarelas=Count(
                "pontuacoes",
                filter=Q(pontuacoes__tipo="AMARELA")
            ),
        )
        .annotate(
            score_fila=ExpressionWrapper(
                F("total_pontos") + F("total_amarelas") * 1.5,
                output_field=FloatField()
            )
        )
        .order_by("score_fila", "id")
    )
    return deque(operadores)


def puxar_da_fila(fila, data, turno, usados_no_dia):
    """
    Lógica inteligente:
    - NOT: garante pelo menos 1 habilitado
    - MAD: validação normal
    """

    tamanho = len(fila)

    # verifica se já há habilitado no NOT
    ja_tem_habilitado = False
    if turno.turno == "NOT":
        ja_tem_habilitado = turno.alocacoes.filter(
            usuario__cursos__codigo="MAN",
        ).exists()

    candidato_habilitado = None

    for _ in range(tamanho):
        op = fila.popleft()

        disponivel = (
            op.id not in usados_no_dia
            and usuario_disponivel(op, data)
        )

        if not disponivel:
            fila.append(op)
            continue

        # ===============================
        # NOTURNO – regra especial
        # ===============================
        if turno.turno == "NOT":

            # se já tem habilitado → qualquer um pode entrar
            if ja_tem_habilitado:
                fila.append(op)
                return op

            # ainda não tem habilitado → guardar o primeiro habilitado encontrado
            if op.cursos.filter(codigo=Curso.MANUTENCAO).exists():
                candidato_habilitado = op

            fila.append(op)
            continue

        # ===============================
        # MADRUGADA (regra normal)
        # ===============================
        if turno.turno == "MAD":
            if pode_assumir_turno(op, "MAD"):
                fila.append(op)
                return op

        fila.append(op)

    # Se for NOT e ainda não tem habilitado,
    # retorna o habilitado encontrado (se houver)
    if turno.turno == "NOT" and not ja_tem_habilitado:
        return candidato_habilitado

    return None
    
def escolher_operador(
    operadores,
    data,
    turno_codigo,
    usados_no_dia,
):
    for op in operadores:
        if op.id in usados_no_dia:
            continue

        if not usuario_disponivel(op, data):
            continue

        if not pode_assumir_turno(op, turno_codigo):
            continue

        return op

    return None

TURNOS_PADRAO = ["MAD", "NOT"]