def calcular_pontos(alocacao):
    dia = alocacao.turno.dia

    # 🔴 NÃO ÚTIL (VERMELHA)
    if dia.tipo_dia == "VERMELHA":
        return 10 if alocacao.foi_acionado else 1

    # ⚫🟡 ÚTEIS
    if dia.tipo_dia in ["PRETA", "AMARELA"]:

        # Titular substituído → 0
        if alocacao.tipo == "TIT" and alocacao.substituido_por.exists():
            return 0

        # Reserva acionado → 1
        if alocacao.tipo == "RES" and alocacao.foi_acionado:
            return 1

        # Titular normal
        if alocacao.tipo == "TIT":
            return 1

    return 0