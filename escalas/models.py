from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.core.exceptions import ValidationError
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
        "TurnoEscala",
        on_delete=models.CASCADE,
        related_name="alocacoes",
    )

    # 🔥 CAMPO NOVO (obrigatório)
    data = models.DateField(db_index=True, null=True, blank=True)

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
        related_name="substituido_por",
    )

    class Meta:
        constraints = [
            # 🚨 REGRA PRINCIPAL
            # usuário só pode aparecer uma vez por dia
            UniqueConstraint(
                fields=["usuario", "data"],
                name="usuario_unico_por_dia",
            ),

            # já existia (mantido)
            UniqueConstraint(
                fields=["turno", "usuario"],
                name="usuario_unico_por_turno",
            ),

            # um reserva por turno
            UniqueConstraint(
                fields=["turno"],
                condition=Q(tipo="RES"),
                name="um_reserva_por_turno",
            ),
        ]

        indexes = [
            models.Index(fields=["data", "usuario"]),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.get_tipo_display()}"

    def clean(self):
        from .utils import pode_assumir_turno

        if not self.usuario:
            return

        # 🚫 Encarregado nunca pode
        if self.usuario.papel == "ENC":
            raise ValidationError("Encarregado não pode ser escalado.")

        # 🔥 Regra especial NOTURNO
        if self.turno.turno == "NOT":

            # verifica se já existe habilitado no turno
            ja_tem_habilitado = self.turno.alocacoes.filter(
                usuario__tem_curso_manutencao=True
            ).exclude(id=self.id).exists()

            # se já tem um habilitado → qualquer um pode entrar
            if ja_tem_habilitado:
                return

            # se ainda não tem → este precisa ser habilitado
            if not self.usuario.tem_curso_manutencao:
                raise ValidationError(
                    "Turno noturno precisa ter pelo menos um operador com curso."
                )

        # MADRUGADA continua validação normal se quiser
        if self.turno.turno == "MAD":
            if not pode_assumir_turno(self.usuario, "MAD"):
                raise ValidationError(
                    "Usuário não possui curso necessário para Madrugada."
                )