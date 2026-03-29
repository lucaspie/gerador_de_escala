from django.utils import timezone
from datetime import timedelta
from escalas.models import AlocacaoEscala
from django.db.models import Count, Q
from .utils import usuario_disponivel, pode_assumir_turno
import random
from indisponibilidades.services import montar_mapa_indisponibilidade

def usuario_disponivel_ctx(op_id, data, ctx):
    return (op_id, data) not in ctx["mapa_indisp"]

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


def puxar_da_fila_fair(
    fila,
    data,
    turno,
    usados_no_dia,
    secao,
    stats=None,
    cursos_por_usuario=None,
    ctx=None
):
    if not fila:
        return None

    if stats is None:
        stats = calcular_stats(secao)

    cursos_por_usuario = cursos_por_usuario or {}
    ctx = ctx or {}

    candidatos = []

    for op in fila:
        if op.id in usados_no_dia:
            continue

        # 🔥 USANDO CTX
        if not usuario_disponivel_ctx(op.id, data, ctx):
            continue

        codigos = cursos_por_usuario.get(op.id, set())

        if turno.turno == "MAD" and not pode_assumir_turno(codigos, "MAD"):
            continue
        if turno.turno == "NOT" and not pode_assumir_turno(codigos, "NOT"):
            continue

        candidatos.append(op)

    if not candidatos:
        return None

    # 🔥 REGRA NOT
    if turno.turno == "NOT":
        ja_tem = any(
            "MAN" in cursos_por_usuario.get(a.usuario_id, set())
            for a in turno.alocacoes.all()
        )

        if not ja_tem:
            habilitados = [
                op for op in candidatos
                if "MAN" in cursos_por_usuario.get(op.id, set())
            ]
            if habilitados:
                candidatos = habilitados

    # mínimos
    min_total = min(stats.get(op.id, {}).get("total", 0) for op in candidatos)
    min_preta = min(stats.get(op.id, {}).get("preta", 0) for op in candidatos)
    min_amarela = min(stats.get(op.id, {}).get("amarela", 0) for op in candidatos)

    candidatos_score = []

    for op in candidatos:
        score = score_usuario(
            stats, op.id, turno,
            min_total, min_preta, min_amarela
        )
        candidatos_score.append((score, op.id, op))

    candidatos_score.sort(key=lambda x: (x[0], x[1]))
    escolhido = candidatos_score[0][2]

    # update incremental
    stats.setdefault(escolhido.id, {"total": 0, "preta": 0, "amarela": 0})
    stats[escolhido.id]["total"] += 1

    if turno.dia.tipo_dia == "PRETA":
        stats[escolhido.id]["preta"] += 1
    elif turno.dia.tipo_dia == "AMARELA":
        stats[escolhido.id]["amarela"] += 1

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
    stats_semana,
    cursos_por_usuario=None,
    ctx=None
):
    cursos_por_usuario = cursos_por_usuario or {}
    ctx = ctx or {}

    candidatos = []

    for op in fila:
        if op.id in usados_no_dia:
            continue

        # 🔥 CTX
        if not usuario_disponivel_ctx(op.id, data, ctx):
            continue

        codigos = cursos_por_usuario.get(op.id, set())

        if turno.turno == "MAD" and not pode_assumir_turno(codigos, "MAD"):
            continue
        if turno.turno == "NOT" and not pode_assumir_turno(codigos, "NOT"):
            continue

        candidatos.append(op)

    if not candidatos:
        return None

    min_semana = min(stats_semana.get(op.id, 0) for op in candidatos)

    min_total = min(stats.get(op.id, {}).get("total", 0) for op in candidatos)
    min_preta = min(stats.get(op.id, {}).get("preta", 0) for op in candidatos)
    min_amarela = min(stats.get(op.id, {}).get("amarela", 0) for op in candidatos)

    candidatos_score = []

    for op in candidatos:
        score_hist = score_usuario(
            stats, op.id, turno,
            min_total, min_preta, min_amarela
        )

        score_semana = stats_semana.get(op.id, 0)

        score = score_semana * 20 + score_hist * 5

        candidatos_score.append((score, op.id, op))

    candidatos_score.sort(key=lambda x: (x[0], x[1]))
    escolhido = candidatos_score[0][2]

    stats_semana[escolhido.id] = stats_semana.get(escolhido.id, 0) + 1

    stats.setdefault(escolhido.id, {"total": 0, "preta": 0, "amarela": 0})
    stats[escolhido.id]["total"] += 1

    if turno.dia.tipo_dia == "PRETA":
        stats[escolhido.id]["preta"] += 1
    elif turno.dia.tipo_dia == "AMARELA":
        stats[escolhido.id]["amarela"] += 1

    fila.remove(escolhido)
    fila.append(escolhido)

    return escolhido