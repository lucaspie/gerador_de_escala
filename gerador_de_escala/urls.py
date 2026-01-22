from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("", include("accounts.urls")),
    path("escalas/", include("escalas.urls")),
    path("permutas/", include("permutas.urls")),
    path("pontuacao/", include("pontuacao.urls")),
    path("relatorios/", include("relatorios.urls")),
    path("indisponibilidades/", include("indisponibilidades.urls")),
]
