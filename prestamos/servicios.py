from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import F, Sum
from django.utils import timezone

from .models import Equipo, Prestamo


def validar_solicitud(*, docente, equipo, cantidad, fecha_prestamo, fecha_devolucion):
    errores = {}
    if fecha_prestamo and fecha_devolucion and fecha_devolucion <= fecha_prestamo:
        errores["fecha_devolucion"] = "La devolución debe ser posterior al préstamo."

    activos = Prestamo.objects.activos()
    if docente and activos.filter(docente=docente).count() >= 3:
        errores["__all__"] = "El docente ya tiene 3 préstamos activos."

    if equipo and equipo.estado != Equipo.Estado.OPERATIVO:
        errores["equipo"] = "Solo se pueden prestar equipos operativos."
    elif equipo and cantidad:
        prestadas = activos.filter(equipo=equipo).aggregate(total=Sum("cantidad", default=0))
        disponibles = equipo.stock_total - prestadas["total"]
        if cantidad > disponibles:
            errores["cantidad"] = f"Hay {max(0, disponibles)} unidades disponibles para préstamo."

    if errores:
        raise ValidationError(errores)


def bloquear_equipo(equipo_id):
    equipos = Equipo.objects.filter(pk=equipo_id)
    if connection.vendor == "sqlite":
        # SQLite no bloquea filas con SELECT FOR UPDATE. La escritura toma el
        # bloqueo antes de leer la disponibilidad, sin cambiar el stock.
        equipos.update(stock_total=F("stock_total"))

    return equipos.select_for_update().get()


@transaction.atomic
def registrar_prestamo(*, docente, equipo, cantidad, fecha_prestamo, fecha_devolucion, observaciones):
    try:
        equipo = bloquear_equipo(equipo.pk)
    except Equipo.DoesNotExist as error:
        raise ValidationError({"equipo": "El equipo ya no está disponible."}) from error

    # El límite también debe cumplirse si el docente solicita equipos diferentes a la vez.
    get_user_model()._default_manager.select_for_update().get(pk=docente.pk)
    validar_solicitud(
        docente=docente, equipo=equipo, cantidad=cantidad,
        fecha_prestamo=fecha_prestamo, fecha_devolucion=fecha_devolucion,
    )
    return Prestamo.objects.create(
        docente=docente, equipo=equipo, cantidad=cantidad, fecha_prestamo=fecha_prestamo,
        fecha_devolucion=fecha_devolucion, observaciones=observaciones,
    )


@transaction.atomic
def registrar_devolucion(prestamo, *, estado_retorno, observaciones_devolucion):
    equipo = bloquear_equipo(prestamo.equipo_id)
    prestamo = Prestamo.objects.select_for_update().get(pk=prestamo.pk)
    if prestamo.devuelto_en is not None:
        raise ValidationError("Este préstamo ya fue devuelto.")

    prestamo.devuelto_en = timezone.now()
    prestamo.estado_retorno = estado_retorno
    prestamo.observaciones_devolucion = observaciones_devolucion
    prestamo.save(update_fields=("devuelto_en", "estado_retorno", "observaciones_devolucion"))

    if equipo.estado != Equipo.Estado.BAJA and estado_retorno != Equipo.Estado.OPERATIVO:
        equipo.estado = estado_retorno
        equipo.save(update_fields=("estado",))

    return prestamo
