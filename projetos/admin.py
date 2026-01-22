from django.contrib import admin
from .models import Projeto, Secao


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    search_fields = ("nome",)


@admin.register(Secao)
class SecaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "projeto", "ativa")
    list_filter = ("projeto",)
