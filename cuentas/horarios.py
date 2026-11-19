from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone


def hora_local(instante):
    if timezone.is_naive(instante):
        raise ValidationError("La fecha y hora debe incluir una zona horaria.")
    return timezone.localtime(instante)


def validar_horario_cita(instante):
    local = hora_local(instante)
    dia = local.weekday()
    cierre = time(13) if dia == 5 else time(18)
    if dia == 6 or not time(8) <= local.time() < cierre:
        raise ValidationError("Atendemos de lunes a viernes de 8:00 a 18:00 y sábados de 8:00 a 13:00.")


def validar_marcacion(instante, objetivo):
    hora_local(instante)
    hora_local(objetivo)
    if abs(instante - objetivo) > timedelta(hours=2):
        raise ValidationError("Marca dentro de las dos horas anteriores o posteriores a tu turno.")


def recordar_marcacion(entrada_programada, marco_entrada, ahora):
    if entrada_programada is None or marco_entrada:
        return None
    local = hora_local(ahora)
    if local.date() != hora_local(entrada_programada).date():
        return None
    return "Todavía no registras tu entrada de hoy."
