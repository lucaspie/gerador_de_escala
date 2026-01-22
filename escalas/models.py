from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from .utils import pode_assumir_turno

User = settings.AUTH_USER_MODEL

class Escala(models.Model):
    class Tipo(models.TextChoices):
        NORMAL = "NOR", "Normal"
        SOBREAVISO = "SOB", "Sobreaviso"

    tipo = models.CharField(
        max_length=3,
        choices=Tipo.choices,
        default=Tipo.NORMAL,
    )
    
    class Status(models.TextChoices):
        RASCUNHO = "RASC", "Rascunho"
        PUBLICADA = "PUB", "Publicada"
        ENCERRADA = "ENC", "Encerrada"

    secao = models.ForeignKey(
        "projetos.Secao",
        on_delete=models.CASCADE,
        related_name="escalas",
    )

    data_inicio = models.DateField(help_text="Segunda-feira")
    data_fim = models.DateField(help_text="Domingo")

    criada_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="escalas_criadas",
    )

    criada_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=4,
        choices=Status.choices,
        default=Status.RASCUNHO,
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["secao", "data_inicio"],
                name="escala_unica_por_secao_semana",
            )
        ]

    def __str__(self):
        return f"Escala {self.secao.nome} ({self.data_inicio} - {self.data_fim})"

class DiaEscala(models.Model):
    class TipoDia(models.TextChoices):
        PRETA = "PRETA", "Dia útil"
        AMARELA = "AMARELA", "Sexta-feira"
        VERMELHA = "VERMELHA", "Não útil / Sobreaviso"

    data = models.DateField()

    tipo_dia = models.CharField(
        max_length=10,
        choices=TipoDia.choices,
    )

    escala = models.ForeignKey(
        Escala,
        on_delete=models.CASCADE,
        related_name="dias",
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["escala", "data"],
                name="dia_unico_por_escala",
            )
        ]

    def __str__(self):
        return f"{self.data} ({self.get_tipo_dia_display()})"

class TurnoEscala(models.Model):
    class Turno(models.TextChoices):
        MADRUGADA = "MAD", "Madrugada"
        NOTURNO = "NOT", "Noturno"
        SOBREAVISO = "SOB", "Sobreaviso"

    dia = models.ForeignKey(
        DiaEscala,
        on_delete=models.CASCADE,
        related_name="turnos",
    )

    turno = models.CharField(
        max_length=3,
        choices=Turno.choices,
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["dia", "turno"],
                name="turno_unico_por_dia",
            )
        ]

    def __str__(self):
        return f"{self.dia.data} - {self.get_turno_display()}"

class AlocacaoEscala(models.Model):
    class Tipo(models.TextChoices):
        TITULAR = "TIT", "Titular"
        RESERVA = "RES", "Reserva"
        SOBREAVISO = "SOB", "Sobreaviso"

    turno = models.ForeignKey(
        TurnoEscala,
        on_delete=models.CASCADE,
        related_name="alocacoes",
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="alocacoes",
        null=True,     
        blank=True,    
    )

    tipo = models.CharField(
        max_length=3,
        choices=Tipo.choices,
    )

    virou_titular = models.BooleanField(default=False)

    foi_acionado = models.BooleanField(
        default=False,
        help_text="Indica se o militar foi acionado no dia não útil",
    )

    substituiu = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="substituido_por"
    )

    class Meta:
        constraints = [
            # Um usuário não pode se repetir no mesmo turno
            UniqueConstraint(
                fields=["turno", "usuario"],
                name="usuario_unico_por_turno",
            ),
            # Apenas UM reserva por turno
            UniqueConstraint(
                fields=["turno"],
                condition=Q(tipo="RES"),
                name="um_reserva_por_turno",
            ),
        ]

    def clean(self):
        if self.usuario.papel == "ENC":
            raise ValueError("Encarregado não pode ser escalado.")

    def __str__(self):
        return f"{self.usuario} - {self.get_tipo_display()}"
    
    def clean(self):
        if self.usuario and self.turno.turno in ["MAD", "NOT"]:
            if not pode_assumir_turno(self.usuario, self.turno.turno):
                raise ValueError(
                    f"{self.usuario} não possui curso necessário para "
                    f"{self.turno.get_turno_display()}."
                )

        if self.usuario and self.usuario.papel == "ENC":
            raise ValueError("Encarregado não pode ser escalado.")
