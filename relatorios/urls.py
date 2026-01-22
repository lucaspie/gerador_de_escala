from django.urls import path
from . import views

app_name = "relatorios"

urlpatterns = [
    path("pontuacao/", views.relatorio_pontuacao_secao, name="pontuacao_secao", ),
    path("pontuacao/excel/", views.exportar_excel, name="exportar_excel", ),
    path("pontuacao/pdf/", views.exportar_pdf, name="exportar_pdf", ),
]
