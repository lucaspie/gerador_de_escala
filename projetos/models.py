from django.db import models


class Projeto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class Secao(models.Model):
    nome = models.CharField(max_length=100)
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name="secoes",
    )
    ativa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} - {self.projeto.nome}"
