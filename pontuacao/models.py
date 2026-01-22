from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Pontuacao(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pontuacoes",
    )

    alocacao = models.ForeignKey(
        "escalas.AlocacaoEscala",
        on_delete=models.CASCADE,
        related_name="pontuacoes",
    )

    pontos = models.PositiveIntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["alocacao"],
                name="pontuacao_unica_por_alocacao",
            )
        ]

    def __str__(self):
        return f"{self.usuario} - {self.pontos} pts"
