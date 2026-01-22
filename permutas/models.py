from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Permuta(models.Model):
    TIPO_CHOICES = (
        ("DIRETA", "Troca direta entre operadores"),
        ("PEDIDO", "Pedido ao escalante"),
    )

    STATUS_CHOICES = (
        ("PENDENTE", "Pendente"),
        ("ACEITA", "Aceita"),
        ("REJEITADA", "Rejeitada"),
        ("CANCELADA", "Cancelada"),
    )

    solicitante = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="permutas_solicitadas",
    )

    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
    )

    alocacao_origem = models.ForeignKey(
        "escalas.AlocacaoEscala",
        on_delete=models.CASCADE,
        related_name="permutas_origem",
    )

    alocacao_destino = models.ForeignKey(
        "escalas.AlocacaoEscala",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="permutas_destino",
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDENTE",
    )

    criada_em = models.DateTimeField(auto_now_add=True)
    resolvida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criada_em"]

    def __str__(self):
        return f"Permuta {self.id} - {self.get_tipo_display()} ({self.status})"
