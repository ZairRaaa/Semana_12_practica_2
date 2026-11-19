from django.conf import settings
from django.db import models
from django.db.models.functions import Coalesce
from django.utils import timezone


class Laboratorio(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class EquipoQuerySet(models.QuerySet):
    def con_disponibilidad(self):
        cantidad_prestada = models.Sum(
            "prestamos__cantidad", filter=models.Q(prestamos__devuelto_en__isnull=True)
        )
        return self.annotate(disponibles=models.F("stock_total") - Coalesce(cantidad_prestada, 0))


class Equipo(models.Model):
    class Estado(models.TextChoices):
        OPERATIVO = "operativo", "Operativo"
        MANTENIMIENTO = "mantenimiento", "En mantenimiento"
        BAJA = "baja", "Dado de baja"

    codigo_patrimonial = models.CharField("código patrimonial", max_length=32, unique=True)
    nombre = models.CharField(max_length=120)
    marca = models.CharField(max_length=80)
    modelo = models.CharField(max_length=80)
    categoria = models.CharField("categoría", max_length=80)
    estado = models.CharField(max_length=16, choices=Estado, default=Estado.OPERATIVO)
    laboratorio = models.ForeignKey(
        Laboratorio, on_delete=models.PROTECT, related_name="equipos"
    )
    stock_total = models.PositiveIntegerField("cantidad total", default=1)
    ultimo_mantenimiento = models.DateField("último mantenimiento", blank=True, null=True)

    objects = EquipoQuerySet.as_manager()

    class Meta:
        ordering = ("nombre", "codigo_patrimonial")
        constraints = [
            models.CheckConstraint(condition=models.Q(stock_total__gt=0), name="equipo_stock_positivo")
        ]

    def __str__(self):
        return f"{self.nombre} ({self.codigo_patrimonial})"

    @property
    def dias_desde_mantenimiento(self):
        if self.ultimo_mantenimiento is None:
            return None
        return (timezone.localdate() - self.ultimo_mantenimiento).days


class PrestamoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(devuelto_en__isnull=True)

    def vencidos(self):
        return self.activos().filter(fecha_devolucion__lt=timezone.localdate())


class Prestamo(models.Model):
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="prestamos_equipo"
    )
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="prestamos")
    cantidad = models.PositiveIntegerField(default=1)
    fecha_prestamo = models.DateField("fecha de préstamo", default=timezone.localdate)
    fecha_devolucion = models.DateField("fecha prevista de devolución")
    observaciones = models.TextField(blank=True, max_length=500)
    devuelto_en = models.DateTimeField("fecha de devolución real", blank=True, null=True)
    estado_retorno = models.CharField(
        "estado al devolver", max_length=16, choices=Equipo.Estado, blank=True
    )
    observaciones_devolucion = models.TextField(
        "observaciones de devolución", blank=True, max_length=500
    )

    objects = PrestamoQuerySet.as_manager()

    class Meta:
        verbose_name = "préstamo"
        verbose_name_plural = "préstamos"
        ordering = ("-fecha_prestamo", "-pk")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="prestamo_cantidad_positiva"
            ),
            models.CheckConstraint(
                condition=models.Q(fecha_devolucion__gt=models.F("fecha_prestamo")),
                name="prestamo_fechas_en_orden",
            ),
        ]
        indexes = [models.Index(fields=["fecha_devolucion"], name="prestamo_fecha_prev_idx")]
        permissions = [
            ("solicitar_prestamo", "Puede solicitar préstamos propios"),
            ("registrar_prestamo", "Puede registrar préstamos para docentes"),
            ("registrar_devolucion", "Puede registrar devoluciones"),
            ("ver_historial_propio", "Puede ver su historial de préstamos"),
            ("enviar_recordatorios", "Puede enviar recordatorios de devolución"),
        ]

    def __str__(self):
        return f"{self.equipo} · {self.docente}"

    @property
    def estado(self):
        if self.devuelto_en is not None:
            return "Devuelto"
        if self.dias_de_retraso:
            return "Vencido"
        return "Activo"

    @property
    def dias_de_retraso(self):
        fecha_final = timezone.localdate(self.devuelto_en) if self.devuelto_en else timezone.localdate()
        return max(0, (fecha_final - self.fecha_devolucion).days)
