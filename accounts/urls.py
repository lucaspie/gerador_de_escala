from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("minhas-escalas/", views.minhas_escalas, name="minhas_escalas"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("usuarios/novo/", views.cadastrar_usuario, name="cadastrar_usuario"),
    path("trocar_senha/", views.TrocarSenhaObrigatoriaView.as_view(), name="trocar_senha"),
    path("usuarios/<int:user_id>/editar/", views.editar_usuario,name="editar_usuario",),
    path("usuarios/", views.lista_usuarios, name="lista_usuarios",),
    path("usuarios/<int:user_id>/resetar-senha/", views.resetar_senha_usuario, name="resetar_senha_usuario",),
]
