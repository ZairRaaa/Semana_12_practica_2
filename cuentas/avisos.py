from .horarios import recordar_marcacion
from .permisos import roles_usuario


def prestamos_vencidos(usuario, prestamos, hoy):
    if "docente" not in roles_usuario(usuario):
        return ()
    cantidad = prestamos.filter(docente_id=usuario.pk, fecha_devolucion__lt=hoy).count()
    return (f"Tienes préstamos vencidos ({cantidad}). Revisa tu historial.",) if cantidad else ()


def citas_pendientes(usuario, citas):
    if "medico" not in roles_usuario(usuario):
        return ()
    cantidad = citas.count()
    return (f"Tienes citas pendientes ({cantidad}). Revisa tu agenda.",) if cantidad else ()


def entrada_pendiente(entrada_programada, marco_entrada, ahora):
    aviso = recordar_marcacion(entrada_programada, marco_entrada, ahora)
    return (aviso,) if aviso else ()
