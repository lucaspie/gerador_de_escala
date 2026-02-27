from dataclasses import dataclass
import statistics
import random

@dataclass
class ParametrosIA:
    peso_pontos: float = 1.0
    peso_amarelas: float = 1.5
    peso_sobreaviso: float = 0.5

    def mutar(self, intensidade=0.2):
        """Gera uma variação aleatória dos parâmetros"""
        return ParametrosIA(
            peso_pontos=self.peso_pontos + random.uniform(-intensidade, intensidade),
            peso_amarelas=self.peso_amarelas + random.uniform(-intensidade, intensidade),
            peso_sobreaviso=self.peso_sobreaviso + random.uniform(-intensidade, intensidade),
        )
    
def avaliar_injustica(resultado: dict[str, int]) -> float:
    valores = list(resultado.values())

    if not valores:
        return 999

    media = statistics.mean(valores)
    desvio = statistics.pstdev(valores)

    # coeficiente de variação
    return desvio / media