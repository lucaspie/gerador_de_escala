from django.contrib import admin
from .models import Escala, DiaEscala, TurnoEscala, AlocacaoEscala


class DiaInline(admin.TabularInline):
    model = DiaEscala
    extra = 0


@admin.register(Escala)
class EscalaAdmin(admin.ModelAdmin):
    list_display = ("secao", "data_inicio", "status")
    list_filter = ("secao", "status")
    inlines = [DiaInline]


@admin.register(TurnoEscala)
class TurnoEscalaAdmin(admin.ModelAdmin):
    list_display = ("dia", "turno")


@admin.register(AlocacaoEscala)
class AlocacaoEscalaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "turno", "tipo", "virou_titular")
    list_filter = ("tipo",)
