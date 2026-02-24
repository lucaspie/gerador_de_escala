from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Pontuacao(models.Model):

    class Tipo(models.TextChoices):
        PRETA = "PRETA", "Preta (Dia útil)"
        AMARELA = "AMARELA", "Amarela (Sexta)"
        VERMELHA = "VERMELHA", "Vermelha (Não útil)"

    class Origem(models.TextChoices):
        ESCALA = "ESC", "Gerada pela Escala"
        MANUAL = "MAN", "Lançamento Manual"
        AJUSTE = "AJU", "Ajuste Administrativo"

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pontuacoes",
    )

    # 🔥 Reintroduzido corretamente
    alocacao = models.ForeignKey(
        "escalas.AlocacaoEscala",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pontuacoes",
        help_text="Preenchido apenas se a pontuação veio da escala",
    )

    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        null=True,
        blank=True,
    )

    origem = models.CharField(
        max_length=3,
        choices=Origem.choices,
        default=Origem.MANUAL,
        null=True,
        blank=True,
    )

    pontos = models.IntegerField()

    observacao = models.CharField(
        max_length=200,
        blank=True,
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.usuario} - {self.tipo} - {self.pontos} pts"