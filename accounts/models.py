from django.contrib.auth.models import AbstractUser
from django.db import models

class Curso(models.TextChoices):
    PISTA = "PIS", "Pista"
    MANUTENCAO = "MAN", "Manutenção"

class CursoOperacional(models.Model):
    codigo = models.CharField(
        max_length=3,
        choices=Curso.choices,
        unique=True,
    )

    def __str__(self):
        return self.get_codigo_display()

class User(AbstractUser):
    class Papel(models.TextChoices):
        ENCARREGADO = "ENC", "Encarregado"
        ESCALANTE = "ESC", "Escalante"
        OPERADOR = "OPE", "Operador"

    secao = models.ForeignKey(
        "projetos.Secao",
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
        help_text="Seção à qual o colaborador pertence",
    )

    papel = models.CharField(
        max_length=3,
        choices=Papel.choices,
        default=Papel.OPERADOR,
    )

    cursos = models.ManyToManyField(
        "accounts.CursoOperacional",
        blank=True,
        related_name="usuarios",
    )

    precisa_trocar_senha = models.BooleanField(
        default=True,
        help_text="Usuário precisa trocar a senha no primeiro login",
    )

    def pode_escalar(self):
        return self.papel in {self.Papel.ENCARREGADO, self.Papel.ESCALANTE}

    def pode_operar(self):
        return self.papel == self.Papel.OPERADOR

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_papel_display()})"
