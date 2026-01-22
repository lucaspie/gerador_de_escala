from django.urls import path
from . import views

app_name = "pontuacao"

urlpatterns = [
    path("relatorio_secao", views.relatorio_secao, name="relatorio_secao"),
    path("minha_pontuacao", views.minha_pontuacao, name="minha_pontuacao"),
]
