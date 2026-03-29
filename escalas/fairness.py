from django.utils import timezone
from datetime import timedelta
from escalas.models import AlocacaoEscala
from django.db.models import Count, Q
from .utils import usuario_disponivel, pode_assumir_turno
import random


# =========================
# STATS BASE (histórico)
# =========================
def calcular_stats(secao, dias=60):
    inicio = timezone.now().date() - timedelta(days=dias)

    alocacoes = (
        AlocacaoEscala.objects
        .filter(
            turno__dia__escala__secao=secao,
            turno__dia__data__gte=inicio,
            tipo="TIT"
        )
        .values("usuario")
        .annotate(
            total=Count("id"),
            preta=Count("id", filter=Q(turno__dia__tipo_dia="PRETA")),
            amarela=Count("id", filter=Q(turno__dia__tipo_dia="AMARELA")),
        )
    )

    stats = {}

    for item in alocacoes:
        stats[item["usuario"]] = {
            "total": item["total"],
            "preta": item["preta"],
            "amarela": item["amarela"],
        }

    return stats


# =========================
# SCORE (estável e previsível)
# =========================
def score_usuario(stats, usuario_id, turno, min_total, min_preta, min_amarela):
    dados = stats.get(usuario_id, {"total": 0, "preta": 0, "amarela": 0})

    total = dados["total"]
    preta = dados["preta"]
    amarela = dados["amarela"]

    score = 0

    # =========================
    # 🔥 REGRA PRINCIPAL (balanceamento global)
    # =========================
    score += (total - min_total) * 10

    # =========================
    # 🔴 Balanceamento dias pesados
    # =========================
    score += (preta - min_preta) * 4

    # =========================
    # 🟡 Balanceamento sexta
    # =========================
    peso_amarela = 3 if turno.dia.tipo_dia == "AMARELA" else 1
    score += (amarela - min_amarela) * peso_amarela

    # =========================
    # 🎲 Ruído mínimo (desempate leve)
    # =========================
    score += random.uniform(0, 0.1)

    return score


# =========================
# FILA JUSTA (core do sistema)
# =========================
def puxar_da_fila_fair(fila, data, turno, usados_no_dia, secao, stats=None):
    """
    Seleção com fairness real:
    - menor carga histórica
    - balanceamento por tipo de dia
    - atualização incremental consistente
    """

    if not fila:
        return None

    # =========================
    # Stats base (somente se necessário)
    # =========================
    if stats is None:
        stats = calcular_stats(secao)

    # =========================
    # Filtrar candidatos válidos
    # =========================
    candidatos = []

    for op in fila:

        if op.id in usados_no_dia:
            continue

        if not usuario_disponivel(op, data):
            continue

        if turno.turno == "MAD" and not pode_assumir_turno(op, "MAD"):
            continue

        if turno.turno == "NOT" and not pode_assumir_turno(op, "NOT"):
            continue

        candidatos.append(op)

    if not candidatos:
        return None

    # =========================
    # Regra NOT (garantir habilitado)
    # =========================
    if turno.turno == "NOT":
        ja_tem_habilitado = turno.alocacoes.filter(
            usuario__cursos__codigo="MAN"
        ).exists()

        if not ja_tem_habilitado:
            habilitados = [
                op for op in candidatos
                if op.cursos.filter(codigo="MAN").exists()
            ]
            if habilitados:
                candidatos = habilitados

    # =========================
    # Calcular mínimos (base fairness)
    # =========================
    min_total = min(
        stats.get(op.id, {}).get("total", 0)
        for op in candidatos
    )

    min_preta = min(
        stats.get(op.id, {}).get("preta", 0)
        for op in candidatos
    )

    min_amarela = min(
        stats.get(op.id, {}).get("amarela", 0)
        for op in candidatos
    )

    # =========================
    # Score + ordenação determinística
    # =========================
    candidatos_score = []

    for op in candidatos:
        score = score_usuario(
            stats,
            op.id,
            turno,
            min_total,
            min_preta,
            min_amarela
        )
        candidatos_score.append((score, op.id, op))

    candidatos_score.sort(key=lambda x: (x[0], x[1]))

    escolhido = candidatos_score[0][2]

    # =========================
    # 🔥 UPDATE INCREMENTAL (ESSENCIAL)
    # =========================
    stats.setdefault(escolhido.id, {"total": 0, "preta": 0, "amarela": 0})

    stats[escolhido.id]["total"] += 1

    if turno.dia.tipo_dia == "PRETA":
        stats[escolhido.id]["preta"] += 1

    elif turno.dia.tipo_dia == "AMARELA":
        stats[escolhido.id]["amarela"] += 1

    # ❗ NÃO rotaciona fila (fairness já decide)
    fila.remove(escolhido)
    fila.append(escolhido)

    return escolhido

def puxar_da_fila_fixa(
    fila,
    data,
    turno,
    usados_no_dia,
    secao,
    stats,
    stats_semana
):
    """
    Versão para escala fixa:
    - fairness histórico (leve)
    - fairness semanal (forte)
    """

    candidatos = []

    for op in fila:

        if op.id in usados_no_dia:
            continue

        if not usuario_disponivel(op, data):
            continue

        if turno.turno == "MAD" and not pode_assumir_turno(op, "MAD"):
            continue

        if turno.turno == "NOT" and not pode_assumir_turno(op, "NOT"):
            continue

        candidatos.append(op)

    if not candidatos:
        return None

    # =========================
    # MÍNIMOS (semana)
    # =========================
    min_semana = min(
        stats_semana.get(op.id, 0)
        for op in candidatos
    )

    # =========================
    # SCORE HÍBRIDO
    # =========================
    candidatos_score = []
    
    min_total = min(stats.get(op.id, {}).get("total", 0) for op in candidatos)
    min_preta = min(stats.get(op.id, {}).get("preta", 0) for op in candidatos)
    min_amarela = min(stats.get(op.id, {}).get("amarela", 0) for op in candidatos)

    for op in candidatos:
        # histórico (leve)
        score_hist = score_usuario(
            stats,
            op.id,
            turno,
            min_total,
            min_preta,
            min_amarela
        )

        # semanal (forte)
        score_semana = stats_semana.get(op.id, 0)

        score = (
            score_semana * 20 +   # 🔥 PRIORIDADE
            score_hist * 5        # leve ajuste histórico
        )

        candidatos_score.append((score, op.id, op))

    candidatos_score.sort(key=lambda x: (x[0], x[1]))

    escolhido = candidatos_score[0][2]

    # =========================
    # UPDATE SEMANA
    # =========================
    stats_semana[escolhido.id] = stats_semana.get(escolhido.id, 0) + 1

    # =========================
    # UPDATE HISTÓRICO (leve)
    # =========================
    stats.setdefault(escolhido.id, {"total": 0, "preta": 0, "amarela": 0})
    stats[escolhido.id]["total"] += 1

    if turno.dia.tipo_dia == "PRETA":
        stats[escolhido.id]["preta"] += 1
    elif turno.dia.tipo_dia == "AMARELA":
        stats[escolhido.id]["amarela"] += 1

    # =========================
    # ROTAÇÃO (IMPORTANTE)
    # =========================
    fila.remove(escolhido)
    fila.append(escolhido)

    return escolhido