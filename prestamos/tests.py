from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cuentas.models import EventoAuditoria

from .models import Equipo, Prestamo


class IntegracionPrestamosTests(TestCase):
    password = "prueba-local-2026"

    @classmethod
    def setUpTestData(cls):
        call_command("configurar_roles", stdout=StringIO())
        call_command("cargar_prestamos_demo", stdout=StringIO())
        usuarios = get_user_model().objects
        cls.docente = usuarios.get(username="demo-lab-ana@uncp.edu.pe")
        cls.asistente = usuarios.get(username="demo-lab-asistente@uncp.edu.pe")
        cls.admin = usuarios.get(username="demo-lab-admin@uncp.edu.pe")
        for usuario in (cls.docente, cls.asistente, cls.admin):
            usuario.set_password(cls.password)
            usuario.save(update_fields=["password"])

    def ingresar(self, usuario, *, follow=False):
        return self.client.post(reverse("ingreso"), {
            "username": usuario.username, "password": self.password,
        }, follow=follow)

    def test_catalogo_publico_y_aviso_de_prestamo_vencido(self):
        self.assertContains(self.client.get(reverse("inicio")), "Ver catálogo")
        self.assertContains(self.client.get(reverse("prestamos:catalogo")), "DEMO-LAB-001")
        respuesta = self.ingresar(self.docente, follow=True)
        self.assertContains(respuesta, "Tienes préstamos vencidos (1)")
        self.assertTrue(respuesta.cookies["laboratorio_sesion"]["httponly"])

    def test_solicitud_y_devolucion_con_roles_y_auditoria(self):
        self.assertEqual(self.ingresar(self.docente).status_code, 302)
        equipo = Equipo.objects.get(codigo_patrimonial="DEMO-LAB-007")
        hoy = timezone.localdate()
        datos = {
            "equipo": equipo.pk, "cantidad": 1,
            "fecha_prestamo": hoy.isoformat(),
            "fecha_devolucion": (hoy + timedelta(days=1)).isoformat(),
            "observaciones": "<b>Práctica</b>",
        }
        respuesta = self.client.post(reverse("prestamos:solicitar"), datos)
        self.assertRedirects(respuesta, reverse("prestamos:historial"))
        prestamo = Prestamo.objects.get(equipo=equipo, docente=self.docente)
        self.assertEqual(prestamo.observaciones, "Práctica")
        self.assertTrue(EventoAuditoria.objects.filter(
            usuario=self.docente, accion="prestamo_creado", recurso=f"prestamo:{prestamo.pk}",
        ).exists())
        devolucion = reverse("prestamos:devolver", args=[prestamo.pk])
        self.assertEqual(self.client.post(devolucion, {"estado_retorno": "operativo"}).status_code, 403)

        self.client.logout()
        self.assertEqual(self.ingresar(self.asistente).status_code, 302)
        respuesta = self.client.post(devolucion, {"estado_retorno": "operativo"})
        self.assertRedirects(respuesta, reverse("prestamos:activos"))
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, "Devuelto")
        self.assertTrue(EventoAuditoria.objects.filter(
            usuario=self.asistente, accion="devolucion_registrada",
            recurso=f"prestamo:{prestamo.pk}",
        ).exists())

    def test_administrador_ve_reportes_y_accion_de_recordatorio(self):
        self.assertEqual(self.ingresar(self.admin).status_code, 302)
        ruta = reverse("admin:prestamos_prestamo_changelist")
        respuesta = self.client.get(ruta, {"estado": "vencido"})
        self.assertContains(respuesta, "Enviar recordatorio de devolución")
        self.assertEqual(respuesta.context["cl"].result_count, 3)
