from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

def validar_permuta(permuta):
    escala = permuta.alocacao_origem.turno.dia.escala

    if escala.status == "ENCERRADA":
        raise ValidationError("Não é possível permutar uma escala encerrada.")

    if permuta.solicitante.papel != "OPE":
        raise ValidationError("Apenas operadores podem solicitar permuta.")

    if permuta.alocacao_origem.usuario != permuta.solicitante:
        raise ValidationError("Você não está alocado neste turno.")


@transaction.atomic
def executar_permuta_direta(permuta):
    origem = permuta.alocacao_origem
    destino = permuta.alocacao_destino

    usuario_origem = origem.usuario
    usuario_destino = destino.usuario

    origem.usuario = None
    origem.save()

    destino.usuario = usuario_origem
    destino.save()

    origem.usuario = usuario_destino
    origem.save()



def executar_pedido_permuta(permuta, novo_usuario):
    """
    Escalante escolhe quem assume o turno
    """
    alocacao = permuta.alocacao_origem
    alocacao.usuario = novo_usuario
    alocacao.save()

    permuta.status = "ACEITA"
    permuta.resolvida_em = timezone.now()
    permuta.save()
