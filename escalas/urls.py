from django.urls import path
from . import views

app_name = "escalas"

urlpatterns = [
    path("criar/", views.criar_escala, name="criar_escala"),
    path("sobreaviso/", views.criar_sobreaviso_view, name="criar_sobreaviso"),
    path("<int:escala_id>/", views.detalhe_escala, name="detalhe_escala"),
    path("<int:escala_id>/publicar/", views.publicar_escala, name="publicar"),
    path("<int:escala_id>/encerrar/", views.encerrar_escala_view, name="encerrar"),
    path("turno/<int:turno_id>/editar/", views.editar_turno, name="editar_turno",),
    path("", views.lista_escalas, name="lista_escalas",),
    path("semanas/", views.semanas_escalante, name="semanas_escalante",),
    path("<int:escala_id>/apagar/", views.apagar_escala, name="apagar_escala",),
    path( "minhas/", views.minhas_escalas, name="minhas_escalas",),
    path("sobreaviso/acionar/<int:alocacao_id>/", views.acionar_sobreaviso, name="acionar_sobreaviso"),
    path("reserva/<int:alocacao_id>/acionar/", views.acionar_reserva, name="acionar_reserva"),
]
