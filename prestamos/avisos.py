from django.utils import timezone

from cuentas.avisos import prestamos_vencidos

from .models import Prestamo


def avisos_ingreso(usuario, ahora):
    return prestamos_vencidos(usuario, Prestamo.objects.activos(), timezone.localdate(ahora))
