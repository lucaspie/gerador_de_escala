from django.utils import timezone
from datetime import timedelta
from escalas.models import AlocacaoEscala
from .utils import usuario_disponivel, pode_assumir_turno
from django.db.models import Sum, Q, Value, Count

def calcular_stats(secao, dias=60):
    inicio = timezone.now().date() - timedelta(days=dias)

    alocacoes = (
        AlocacaoEscala.objects
        .filter(turno__dia__escala__secao=secao,
                turno__dia__data__gte=inicio,
                tipo="TIT")
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

def score_usuario(stats, usuario_id, media_total, media_preta, media_amarela, turno):
    dados = stats.get(usuario_id, {"total": 0, "preta": 0, "amarela": 0})

    total = dados["total"]
    preta = dados["preta"]
    amarela = dados["amarela"]

    score = 0

    # 🔴 Penalização forte para PRETA acima da média
    score += max(0, preta - media_preta) * 5

    # 🟡 Penalização moderada para TOTAL acima da média
    score += max(0, total - media_total) * 3

    # 🟡 AMARELA — equilíbrio real
    if turno.dia.tipo_dia == "AMARELA":
        # quem tem poucas amarelas ganha bônus
        score -= max(0, media_amarela - amarela) * 4
        # quem tem muitas amarelas perde prioridade
        score += max(0, amarela - media_amarela) * 2
    else:
        # leve peso global
        score += amarela * 0.5

    # 🟢 Bônus de recuperação geral
    if total < media_total:
        score -= 2

    return score    

import random

def puxar_da_fila_fair(fila, data, turno, usados_no_dia, secao):
    candidatos = []
    stats = calcular_stats(secao)

    usuarios_ids = [u.id for u in fila]

    if not usuarios_ids:
        return None

    media_total = (
        sum(stats.get(uid, {}).get("total", 0) for uid in usuarios_ids)
        / len(usuarios_ids)
    )

    media_preta = (
        sum(stats.get(uid, {}).get("preta", 0) for uid in usuarios_ids)
        / len(usuarios_ids)
    )

    media_amarela = (
        sum(stats.get(uid, {}).get("amarela", 0) for uid in usuarios_ids)
        / len(usuarios_ids)
    )

    for op in list(fila):

        if op.id in usados_no_dia:
            continue

        if not usuario_disponivel(op, data):
            continue

        if turno.turno == "MAD" and not pode_assumir_turno(op, "MAD"):
            continue

        score = score_usuario(stats, op.id, media_total, media_preta, media_amarela, turno)
        candidatos.append((score, random.random(), op))

    if not candidatos:
        return None

    candidatos.sort(key=lambda x: (x[0], x[1]))
    escolhido = candidatos[0][2]

    fila.remove(escolhido)
    fila.append(escolhido)

    if turno.turno == "NOT":
        ja_tem_habilitado = turno.alocacoes.filter(
            usuario__cursos__codigo="MAN"
        ).exists()

        if not ja_tem_habilitado:
            habilitados = [
                c for c in candidatos
                if c[2].cursos.filter(codigo="MAN").exists()
            ]
            if habilitados:
                habilitados.sort(key=lambda x: (x[0], x[1]))
                escolhido = habilitados[0][2]

    return escolhido