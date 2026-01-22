def calcular_pontos(alocacao):
    """
    Regras finais de pontuação:

    - PRETA / AMARELA:
        TITULAR = 1 ponto
        RESERVA não acionado = 0
        RESERVA acionado = 1

    - VERMELHA (SOBREAVISO):
        NÃO acionado = 1 ponto
        ACIONADO = 10 pontos
    """

    dia = alocacao.turno.dia

    # 🟥 DIA NÃO ÚTIL — SOBREAVISO
    if dia.tipo_dia == "VERMELHA":
        return 10 if alocacao.foi_acionado else 1

    if dia.tipo_dia in ["PRETA", "AMARELA"]:

        # Titular substituído → 0
        if alocacao.tipo == "TIT" and hasattr(alocacao, "substituido_por") and alocacao.substituido_por.exists():
            return 0

        # Reserva acionado → 1
        if alocacao.tipo == "RES" and alocacao.foi_acionado:
            return 1

        # Titular normal → 1
        if alocacao.tipo == "TIT":
            return 1
    return 0

