from dataclasses import dataclass
from datetime import datetime


@dataclass
class Plantao:
    data: datetime
    tipo: str  # madruga, noturno, diurno, sobreaviso

    def peso_emocional(self):
        pesos = {  
            "madruga": 3,
            "noturno": 2,
            "diurno": 1,
            "sobreaviso_acionado": 10,
            "sobreaviso": 1
        }
        return pesos.get(self.tipo, 1)
    
class UsuarioEscala:
    def __init__(self, nome: str, historico_dict: dict[str, str]):
        self.nome = nome
        self.plantoes = self._parse_historico(historico_dict)

    def _parse_historico(self, historico):
        lista = []
        for data_str, tipo in historico.items():
            data = datetime.strptime(data_str, "%d/%m/%Y")
            lista.append(Plantao(data, tipo))
        return sorted(lista, key=lambda p: p.data)
    
    def carga_total(self):
        return sum(p.peso_emocional() for p in self.plantoes)
    
    def dias_desde_ultimo(self):
        if not self.plantoes:
            return 999

        ultimo = self.plantoes[-1].data
        return (datetime.now() - ultimo).days
    
    def sequencia_recente(self, janela_dias=7):
        hoje = datetime.now()
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
    
class MotorEscalaIA:
    def __init__(self, usuarios: list[UsuarioEscala]):
        self.usuarios = usuarios

    def escolher_mais_justo(self):
        melhor = None
        menor_score = float("inf")

        for u in self.usuarios:
            score = u.score_fairness()
            print(f"{u.nome}: {score:.2f}")

            if score < menor_score:
                menor_score = score
                melhor = u

        return melhor