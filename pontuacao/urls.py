from django.urls import path
from . import views

app_name = "pontuacao"

urlpatterns = [
    path("relatorio_secao", views.relatorio_secao, name="relatorio_secao"),
    path("minha_pontuacao", views.minha_pontuacao, name="minha_pontuacao"),
    path("lancar/<int:alocacao_id>/", views.lancar_pontos, name="lancar"),
    path("painel/", views.painel_pontuacao, name="painel"),
    path("operador/<int:user_id>/", views.pontuar_operador, name="operador"),
    path("pisteiro_manual/<int:user_id>", views.lancar_pisteiro_manual, name="lancar_pisteiro_manual"),
]
