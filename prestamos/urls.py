from django.urls import path

from . import views

app_name = "prestamos"

urlpatterns = [
    path("", views.catalogo, name="catalogo"),
    path("solicitar/", views.solicitar, name="solicitar"),
    path("registrar/", views.registrar, name="registrar"),
    path("mis-prestamos/", views.historial, name="historial"),
    path("devoluciones/", views.activos, name="activos"),
    path("devoluciones/<int:prestamo_id>/", views.devolver, name="devolver"),
]
