from escalas.ia.simulador import SimuladorEscala
from escalas.ia.autoajuste import ParametrosIA, avaliar_injustica

def treinar_ia(secao, geracoes=30, semanas=100):
    melhor = ParametrosIA()
    melhor_score = 999

    historico = []

    for g in range(geracoes):
        candidato = melhor.mutar()

        sim = SimuladorEscala(secao, params=candidato)
        resultado = sim.rodar(semanas)

        score = avaliar_injustica(resultado)
        historico.append(score)

        print(f"Geração {g} → injustiça {score:.5f}")

        if score < melhor_score:
            melhor = candidato
            melhor_score = score
            print("⭐ NOVO MELHOR!")

    print("\n🏆 MELHOR CONFIG:")
    print(melhor)
    print(f"Injustiça final: {melhor_score:.5f}")

    return melhor, historico