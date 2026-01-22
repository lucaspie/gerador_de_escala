# indisponibilidades/models.py
from django.conf import settings
from django.db import models
from django.db.models import Q, F

User = settings.AUTH_USER_MODEL


class Indisponibilidade(models.Model):
    class Motivo(models.TextChoices):
        MEDICA = "MED", "Consulta médica"
        FERIAS = "FER", "Férias"
        CURSO = "CUR", "Curso"
        FOLGA = "FOL", "Folga"
        OUTRO = "OUT", "Outro"

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="indisponibilidades",
    )

    data_inicio = models.DateField()
    data_fim = models.DateField()

    motivo = models.CharField(
        max_length=3,
        choices=Motivo.choices,
    )

    observacao = models.CharField(
        max_length=255,
        blank=True,
    )

    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data_inicio"]
        constraints = [
            models.CheckConstraint(
                condition=Q(data_fim__gte=F("data_inicio")),
                name="data_fim_maior_ou_igual_inicio",
            )

        ]

    def __str__(self):
        return f"{self.usuario} | {self.data_inicio} → {self.data_fim}"

    def cobre_data(self, data):
        return self.data_inicio <= data <= self.data_fim
