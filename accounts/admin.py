from django.contrib import admin
from .models import User, CursoOperacional


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "first_name", "papel", "secao", "is_active")
    list_filter = ("papel", "secao")
    search_fields = ("username", "first_name", "last_name")

@admin.register(CursoOperacional)
class CursoOperacionalAdmin(admin.ModelAdmin):
    list_display = ("codigo", "get_codigo_display")
    ordering = ("codigo",)