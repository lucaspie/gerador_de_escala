from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from escalas.models import AlocacaoEscala


def validar_permuta(permuta):
    escala = permuta.alocacao_origem.turno.dia.escala

    if escala.status == "ENCERRADA":
        raise ValidationError("Não é possível permutar uma escala encerrada.")

    if permuta.solicitante.papel != "OPE":
        raise ValidationError("Apenas operadores podem solicitar permuta.")

    if permuta.alocacao_origem.usuario != permuta.solicitante:
        raise ValidationError("Você não está alocado neste turno.")


def usuario_ja_escala_no_dia(usuario, dia, ignorar_alocacao=None):
    qs = AlocacaoEscala.objects.filter(
        turno__dia=dia,
        usuario=usuario,
    )
    if ignorar_alocacao:
        qs = qs.exclude(id=ignorar_alocacao.id)
    return qs.exists()


@transaction.atomic
def executar_permuta_direta(permuta):
    validar_permuta(permuta)

    origem = permuta.alocacao_origem
    destino = permuta.alocacao_destino

    if not destino:
        raise ValidationError("Permuta direta precisa de um destino.")

    usuario_origem = origem.usuario
    usuario_destino = destino.usuario

    if not usuario_origem or not usuario_destino:
        raise ValidationError("Ambos os turnos precisam ter usuários.")

    dia_origem = origem.turno.dia
    dia_destino = destino.turno.dia

    # validação só se dias diferentes
    if dia_origem != dia_destino:
        if usuario_ja_escala_no_dia(usuario_origem, dia_destino, origem):
            raise ValidationError("Usuário já escalado no dia destino.")

        if usuario_ja_escala_no_dia(usuario_destino, dia_origem, destino):
            raise ValidationError("Usuário destino já escalado no dia origem.")

    # ✅ SWAP SEGURO EM 3 PASSOS
    origem.usuario = None
    origem.save(update_fields=["usuario"])

    destino.usuario = usuario_origem
    destino.save(update_fields=["usuario"])

    origem.usuario = usuario_destino
    origem.save(update_fields=["usuario"])

    permuta.status = "ACEITA"
    permuta.resolvida_em = timezone.now()
    permuta.save()


def executar_pedido_permuta(permuta, novo_usuario):
    validar_permuta(permuta)

    alocacao = permuta.alocacao_origem
    dia = alocacao.turno.dia

    conflito = AlocacaoEscala.objects.filter(
        turno__dia=dia,
        usuario=novo_usuario,
    ).exclude(id=alocacao.id).exists()

    if conflito:
        raise ValidationError("Este usuário já está escalado neste dia.")

    alocacao.usuario = novo_usuario
    alocacao.save()

    permuta.status = "ACEITA"
    permuta.resolvida_em = timezone.now()
    permuta.save()