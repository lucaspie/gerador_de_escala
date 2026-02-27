class MotorEscalaIA:
    def __init__(self, usuarios):
        self.usuarios = usuarios

    def escolher(self, debug=False):
        melhor = None
        menor = float("inf")

        for u in self.usuarios:
            score = u.score_fairness()

            if debug:
                print(f"{u.nome}: {score:.2f}")

            if score < menor:
                menor = score
                melhor = u

        return melhor