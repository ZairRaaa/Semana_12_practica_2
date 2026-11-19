from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def roles_usuario(usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        return set()
    nombres = usuario.groups.values_list("name", flat=True)
    return {rol for rol, nombre in settings.CASO.roles.items() if nombre in nombres}


def exige_rol(usuario, *roles):
    if roles_usuario(usuario).isdisjoint(roles):
        raise PermissionDenied


def requiere_rol(*roles):
    def decorar(vista):
        @login_required
        @wraps(vista)
        def protegida(request, *args, **kwargs):
            exige_rol(request.user, *roles)
            return vista(request, *args, **kwargs)
        return protegida
    return decorar


def historial_prestamos(usuario, prestamos):
    exige_rol(usuario, "docente")
    return prestamos.filter(docente_id=usuario.pk)


def historial_clinico(usuario, paciente_usuario_id):
    roles = roles_usuario(usuario)
    if "medico" in roles or ("paciente" in roles and usuario.pk == paciente_usuario_id):
        return
    raise PermissionDenied


def agendar_cita(usuario, paciente_usuario_id):
    roles = roles_usuario(usuario)
    if "recepcionista" in roles or ("paciente" in roles and usuario.pk == paciente_usuario_id):
        return
    raise PermissionDenied


def cancelar_cita(usuario, paciente_usuario_id):
    roles = roles_usuario(usuario)
    if roles & {"recepcionista", "medico"} or (
        "paciente" in roles and usuario.pk == paciente_usuario_id
    ):
        return
    raise PermissionDenied


def aprobar_permiso(usuario, area_jefe_id, area_solicitud_id):
    roles = roles_usuario(usuario)
    if "rrhh" in roles or (
        "jefe" in roles and area_jefe_id is not None and area_jefe_id == area_solicitud_id
    ):
        return
    raise PermissionDenied


def expediente_empleado(usuario, empleado_usuario_id):
    roles = roles_usuario(usuario)
    if "rrhh" in roles or (roles and usuario.pk == empleado_usuario_id):
        return
    raise PermissionDenied


def reportes_area(usuario, area_jefe_id, area_reporte_id):
    aprobar_permiso(usuario, area_jefe_id, area_reporte_id)


def reportes_asistencia(usuario, metodo):
    exige_rol(usuario, *("rrhh", "contador") if metodo in {"GET", "HEAD"} else ("rrhh",))

def puede_auditar(usuario):
    rol = "rrhh" if settings.CASO_ACTIVO == "asistencia" else "admin"
    return usuario.is_superuser or rol in roles_usuario(usuario)
