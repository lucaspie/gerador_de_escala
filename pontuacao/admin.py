from django.contrib import admin
from .models import Pontuacao


@admin.register(Pontuacao)
class PontuacaoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "pontos", "criado_em")
    list_filter = ("usuario",)
