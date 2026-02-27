from dataclasses import dataclass
from datetime import datetime, date


@dataclass
class Plantao:
    data: date
    tipo: str

    def peso_emocional(self):
        pesos = {
            "MAD": 3,
            "NOT": 2,
            "SOB_ATIVO": 10,
            "SOB": 1,
        }
        return pesos.get(self.tipo, 1)


class UsuarioEscala:
    def __init__(self, user_id: int, nome: str, plantoes: list[Plantao]):
        self.user_id = user_id
        self.nome = nome
        self.plantoes = sorted(plantoes, key=lambda p: p.data)

    # ------------------------
    # MÉTRICAS IA
    # ------------------------

    def carga_total(self):
        return sum(p.peso_emocional() for p in self.plantoes)

    def dias_desde_ultimo(self):
        if not self.plantoes:
            return 999
        return (date.today() - self.plantoes[-1].data).days

    def sequencia_recente(self, janela_dias=7):
        hoje = date.today()
        count = 0
        for p in reversed(self.plantoes):
            if (hoje - p.data).days <= janela_dias:
                count += 1
            else:
                break
        return count

    def score_fairness(self):
        carga = self.carga_total() * 0.5
        sequencia = self.sequencia_recente() * 2
        descanso = self.dias_desde_ultimo() * 0.3
        return carga + sequencia - descanso