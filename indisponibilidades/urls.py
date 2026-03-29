# indisponibilidades/urls.py
from django.urls import path
from . import views

app_name = "indisponibilidades"

urlpatterns = [
    path("minhas/", views.minhas_indisponibilidades, name="minhas"),
    path("nova/", views.criar_indisponibilidade, name="nova"),
    path("<int:pk>/excluir/", views.excluir_indisponibilidade, name="excluir"),
    path("secao/", views.indisponibilidades_secao, name="secao"),
    path("aprovar/<int:pk>/", views.aprovar_indisponibilidade, name="aprovar"),
    path("recusar/<int:pk>/", views.recusar_indisponibilidade, name="recusar"),
]
