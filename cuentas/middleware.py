from django.conf import settings
from django.contrib import messages
from django.contrib.auth import SESSION_KEY, logout
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.utils import timezone
from django.utils.module_loading import import_string

from .auditoria import registrar


class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 403:
            ruta = request.resolver_match
            registrar(request, "acceso_denegado", 403, ruta.view_name if ruta else "")
        return response


class SesionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        if SESSION_KEY in request.session and not usuario.is_authenticated:
            registrar(request, "sesion_revocada", 403)
            logout(request)
            return redirect_to_login(request.get_full_path())

        if usuario.is_authenticated:
            ahora = int(timezone.now().timestamp())
            anterior = request.session.get("ultima_actividad", ahora)
            if ahora - anterior >= settings.SESSION_COOKIE_AGE:
                registrar(request, "sesion_inactiva", 403)
                logout(request)
                messages.info(request, "Tu sesión terminó por inactividad. Ingresa de nuevo.")
                return redirect_to_login(request.get_full_path())
            request.session["ultima_actividad"] = ahora

        return self.get_response(request)


class AvisosIngresoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        ruta = settings.AVISOS_INGRESO
        self.avisos = import_string(ruta) if ruta else None

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(request, "ingreso_exitoso", False) and self.avisos:
            for aviso in self.avisos(request.user, timezone.now()):
                messages.warning(request, aviso)
        return response


def controla_horario(validar):
    """El validador recibe request y parámetros de URL obtenidos en el servidor."""
    def decorar(vista):
        vista.validar_horario = validar
        return vista
    return decorar


class HorarioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        validar = getattr(view_func, "validar_horario", None)
        if not validar or request.method != "POST" or not request.user.is_authenticated:
            return None
        try:
            validar(request, *view_args, **view_kwargs)
        except ValidationError as error:
            return HttpResponseBadRequest(" ".join(error.messages), content_type="text/plain")
        return None
