from django.urls import path
from . import views

app_name = "permutas"

urlpatterns = [
    # Operador
    path("minhas/", views.minhas_permutas, name="minhas_permutas"),
    path("direta/<int:alocacao_id>/", views.solicitar_permuta_direta, name="direta"),
    path("pedido/<int:alocacao_id>/", views.solicitar_pedido_permuta, name="pedido"),

    # Escalante
    path("pedidos/", views.pedidos_permuta, name="pedidos"),
    path("pedidos/<int:permuta_id>/aprovar/", views.aprovar_pedido, name="aprovar"),
    path("pedidos/<int:permuta_id>/rejeitar/", views.rejeitar_pedido, name="rejeitar"),

    path("recebidas/", views.permutas_recebidas, name="recebidas"),
    path("direta/<int:permuta_id>/aceitar/", views.aceitar_permuta_direta, name="aceitar_direta"),
    path("direta/<int:permuta_id>/rejeitar/", views.rejeitar_permuta_direta, name="rejeitar_direta"),
]
