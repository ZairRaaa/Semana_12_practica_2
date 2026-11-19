from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .casos import CASOS
from .horarios import validar_horario_cita, validar_marcacion
from .models import EventoAuditoria
from .permisos import (
    agendar_cita, aprobar_permiso, cancelar_cita, exige_rol, historial_clinico,
    reportes_asistencia,
)


def avisos_prueba(usuario, ahora):
    return ('Tienes préstamos vencidos (2).',) if usuario.is_authenticated else ()


@override_settings(CASO=CASOS["laboratorio"], CASO_ACTIVO="laboratorio", SESSION_COOKIE_AGE=1800)
class AccesoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("configurar_roles", verbosity=0)
        cls.usuario = get_user_model().objects.create_user(
            "docente@uncp.edu.pe", password="Clave-local-para-pruebas-81",
        )
        cls.usuario.groups.add(Group.objects.get(name="Docente"))

    def ingresar(self, **extras):
        return self.client.post(reverse("ingreso"), {
            "username": self.usuario.username.upper(),
            "password": "Clave-local-para-pruebas-81",
            **extras,
        })

    def test_login_logout_y_cookie(self):
        respuesta = self.ingresar(next="https://otro.invalid/")
        self.assertRedirects(respuesta, reverse("panel"))
        cookie = respuesta.cookies[settings.SESSION_COOKIE_NAME]
        self.assertEqual(int(cookie["max-age"]), 1800)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(self.client.get(reverse("salida")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("salida")), reverse("inicio"))
        self.assertRedirects(self.client.get(reverse("panel")), "/ingresar/?next=/mi-cuenta/")

    def test_csrf_obligatorio(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse("ingreso")).status_code, 403)

    def test_docente_denegado_y_admin_autorizado(self):
        self.ingresar()
        self.assertEqual(self.client.get(reverse("auditoria")).status_code, 403)
        self.assertTrue(EventoAuditoria.objects.filter(
            accion="acceso_denegado", usuario=self.usuario, recurso="auditoria",
        ).exists())
        self.usuario.groups.add(Group.objects.get(name="Administrador"))
        self.assertContains(self.client.get(reverse("auditoria")), "acceso_denegado")

    def test_inactividad_y_revocacion(self):
        self.ingresar()
        ahora = timezone.now()
        with patch("cuentas.middleware.timezone.now", return_value=ahora + timedelta(minutes=30)):
            self.assertRedirects(self.client.get(reverse("panel")), "/ingresar/?next=/mi-cuenta/")
        self.ingresar()
        get_user_model().objects.filter(pk=self.usuario.pk).update(is_active=False)
        self.assertRedirects(self.client.get(reverse("panel")), "/ingresar/?next=/mi-cuenta/")
        self.assertTrue(EventoAuditoria.objects.filter(accion="sesion_revocada").exists())

    @override_settings(AVISOS_INGRESO="cuentas.tests.avisos_prueba")
    def test_aviso_solo_se_muestra_al_ingresar(self):
        self.assertContains(self.client.get(reverse("ingreso")), "Iniciar sesión")
        self.ingresar()
        self.assertContains(self.client.get(reverse("panel")), "Tienes préstamos vencidos (2).")
        self.assertNotContains(self.client.get(reverse("panel")), "Tienes préstamos vencidos (2).")

    def test_devolucion_limitada_al_asistente(self):
        with self.assertRaises(PermissionDenied):
            exige_rol(self.usuario, "asistente")
        self.usuario.groups.add(Group.objects.get(name="Asistente"))
        exige_rol(self.usuario, "asistente")


class PoliticasTests(TestCase):
    def cuenta(self, grupo):
        usuario = get_user_model().objects.create_user(grupo)
        usuario.groups.add(Group.objects.create(name=grupo))
        return usuario

    @override_settings(CASO=CASOS["consultas"])
    def test_paciente_solo_gestiona_su_propia_informacion(self):
        paciente = self.cuenta("Pacientes")
        for politica in (historial_clinico, agendar_cita, cancelar_cita):
            politica(paciente, paciente.pk)
            with self.assertRaises(PermissionDenied):
                politica(paciente, paciente.pk + 1)

    @override_settings(CASO=CASOS["asistencia"])
    def test_aprobacion_por_area_y_contador_de_solo_lectura(self):
        jefe = self.cuenta("Jefes de área")
        contador = self.cuenta("Contadores")
        aprobar_permiso(jefe, 1, 1)
        with self.assertRaises(PermissionDenied):
            aprobar_permiso(jefe, 1, 2)
        reportes_asistencia(contador, "GET")
        with self.assertRaises(PermissionDenied):
            reportes_asistencia(contador, "POST")

    def test_limites_de_horario(self):
        sabado = datetime(2026, 11, 21, 8, tzinfo=ZoneInfo("America/Lima"))
        validar_horario_cita(sabado)
        with self.assertRaises(ValidationError):
            validar_horario_cita(sabado + timedelta(hours=5))
        validar_marcacion(sabado + timedelta(hours=2), sabado)
        with self.assertRaises(ValidationError):
            validar_marcacion(sabado + timedelta(hours=2, seconds=1), sabado)
