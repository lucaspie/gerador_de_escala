# escalas/ia/simulador.py

from collections import defaultdict
from datetime import timedelta
from accounts.models import User
from indisponibilidades.models import Indisponibilidade
from escalas.ia.autoajuste import ParametrosIA
import random
import statistics

TURNOS = ["MAD", "NOT"]

def indisponivel(user_id, data):
        return Indisponibilidade.objects.filter(
            usuario_id=user_id,
            data_inicio__lte=data,
            data_fim__gte=data,
        ).exists()

class OperadorIA:
    def __init__(self, user):
        self.id = user.id
        self.nome = user.username
        self.cursos = set(user.cursos.values_list("codigo", flat=True))

        self.pontos = 0
        self.amarelas = 0
        self.sobreavisos = 0
        self.sobreavisos_acionados = 0

    def pode_turno(self, turno):
        if turno == "MAD":
            return "PIS" in self.cursos
        if turno == "NOT":
            return "MAN" in self.cursos
        return False
    
    def tem_man(self):
        return "MAN" in self.cursos

    def pode_madrugada(self):
        return "PIS" in self.cursos
    
class SimuladorEscala:
    def __init__(self, secao, params=None):
        users = User.objects.filter(secao=secao, papel="OPE")
        self.ops = [OperadorIA(u) for u in users]
        self.params = params or ParametrosIA()

    def score(self, op):
        return (
            op.pontos * self.params.peso_pontos +
            op.amarelas * self.params.peso_amarelas +
            op.sobreavisos * self.params.peso_sobreaviso
        )

    def escolher(self, data, turno, usados):
        candidatos = sorted(self.ops, key=self.score)

        for op in candidatos:
            if op.id in usados:
                continue
            if indisponivel(op.id, data):
                continue
            if not op.pode_turno(turno):
                continue
            return op

        return None
    
    def simular_sobreaviso(self, data):
        candidatos = sorted(self.ops, key=lambda o: o.sobreavisos)

        escolhido = candidatos[0]

        escolhido.sobreavisos += 1
        escolhido.pontos += 1

        # chance de acionamento (ajustável)
        if random.random() < 0.25:
            escolhido.sobreavisos_acionados += 1
            escolhido.pontos += 9  # já ganhou 1 antes

    def escolher_noturno(self, data, usados):
        candidatos = sorted(self.ops, key=self.score)

        dupla = []

        # primeiro tenta alguém com manutenção
        for op in candidatos:
            if op.id in usados:
                continue
            if indisponivel(op.id, data):
                continue
            if op.tem_man():
                dupla.append(op)
                usados.add(op.id)
                break

        # se ninguém com MAN, cancela turno
        if not dupla:
            return []

        # segundo slot pode ser qualquer um disponível
        for op in candidatos:
            if op.id in usados:
                continue
            if indisponivel(op.id, data):
                continue
            dupla.append(op)
            usados.add(op.id)
            break

        return dupla
    
    def simular_semana(self, data_inicio):
        distribuicao = defaultdict(int)

        for i in range(7):
            data = data_inicio + timedelta(days=i)
            weekday = data.weekday()

            tipo = (
                "PRETA" if weekday < 4
                else "AMARELA" if weekday == 4
                else "VERMELHA"
            )

            if tipo == "VERMELHA":
                continue

            for turno in TURNOS:
                usados = set()

                op = self.escolher(data, turno, usados)
                if not op:
                    continue

                usados.add(op.id)

                # pontuação fake
                if tipo == "PRETA":
                    op.pontos += 1
                elif tipo == "AMARELA":
                    op.pontos += 2
                    op.amarelas += 1

                distribuicao[op.nome] += 1

        return distribuicao
    
    def analisar(self, resultado):
        valores = list(resultado.values())

        media = statistics.mean(valores)
        desvio = statistics.pstdev(valores)
        gap = max(valores) - min(valores)

        coef_var = desvio / media  # índice de desigualdade

        print(f"Média: {media:.2f}")
        print(f"Desvio: {desvio:.2f}")
        print(f"Gap: {gap}")
        print(f"Coeficiente de variação: {coef_var:.4f}")
    
    def rodar(self, semanas=100):
        from datetime import date
        inicio = date.today()

        resultados = defaultdict(int)

        for s in range(semanas):
            semana = self.simular_semana(inicio + timedelta(days=s * 7))
            #self.simular_sobreaviso(data)
            for nome, qtd in semana.items():
                resultados[nome] += qtd

        return resultados