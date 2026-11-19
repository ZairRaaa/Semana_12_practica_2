from django import forms
from django.contrib import admin, messages
from django.core.mail import send_mass_mail
from django.utils import timezone
from django.utils.html import format_html

from .eventos import registrar_evento
from .models import Equipo, Laboratorio, Prestamo
from .servicios import bloquear_equipo


@admin.register(Laboratorio)
class LaboratorioAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)


class EquipoAdminForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = "__all__"

    def clean_stock_total(self):
        stock = self.cleaned_data["stock_total"]
        if self.instance.pk:
            bloquear_equipo(self.instance.pk)
            equipo = Equipo.objects.con_disponibilidad().get(pk=self.instance.pk)
            prestadas = equipo.stock_total - equipo.disponibles
            if stock < prestadas:
                raise forms.ValidationError(f"Hay {prestadas} unidades prestadas actualmente.")
        return stock


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    form = EquipoAdminForm
    list_display = (
        "codigo_patrimonial", "nombre", "categoria", "laboratorio",
        "estado_visual", "stock_total", "dias_mantenimiento",
    )
    list_filter = ("laboratorio", "estado")
    search_fields = ("codigo_patrimonial", "nombre", "categoria")
    list_select_related = ("laboratorio",)
    actions = ("marcar_mantenimiento",)

    @admin.display(description="Estado", ordering="estado")
    def estado_visual(self, equipo):
        colores = {
            Equipo.Estado.OPERATIVO: "#187346",
            Equipo.Estado.MANTENIMIENTO: "#966200",
            Equipo.Estado.BAJA: "#b72a3a",
        }
        return format_html('<span style="color: {}; font-weight: 700">{}</span>',
                           colores[equipo.estado], equipo.get_estado_display())

    @admin.display(description="Días desde el último mantenimiento", empty_value="Sin fecha")
    def dias_mantenimiento(self, equipo):
        return equipo.dias_desde_mantenimiento

    @admin.action(description="Marcar como en mantenimiento", permissions=["change"])
    def marcar_mantenimiento(self, request, queryset):
        cantidad = queryset.exclude(estado=Equipo.Estado.BAJA).update(
            estado=Equipo.Estado.MANTENIMIENTO
        )
        self.message_user(request, f"Equipos marcados en mantenimiento: {cantidad}.")

    def delete_model(self, request, obj):
        equipo_id = obj.pk
        super().delete_model(request, obj)
        registrar_evento(request, "eliminacion", equipo_id=equipo_id)

    def delete_queryset(self, request, queryset):
        equipos_ids = list(queryset.values_list("pk", flat=True))
        super().delete_queryset(request, queryset)
        for equipo_id in equipos_ids:
            registrar_evento(request, "eliminacion", equipo_id=equipo_id)


class FiltroEstadoPrestamo(admin.SimpleListFilter):
    title = "estado"
    parameter_name = "estado"

    def lookups(self, request, model_admin):
        return (("activo", "Activo"), ("vencido", "Vencido"), ("devuelto", "Devuelto"))

    def queryset(self, request, queryset):
        if self.value() == "activo":
            return queryset.activos().filter(fecha_devolucion__gte=timezone.localdate())
        if self.value() == "vencido":
            return queryset.vencidos()
        if self.value() == "devuelto":
            return queryset.filter(devuelto_en__isnull=False)
        return queryset


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = (
        "docente", "equipo", "fecha_prestamo", "fecha_devolucion", "estado_actual", "retraso",
    )
    list_filter = (
        FiltroEstadoPrestamo, "fecha_prestamo", "fecha_devolucion", "docente", "equipo__laboratorio",
    )
    search_fields = (
        "equipo__codigo_patrimonial", "docente__username", "docente__first_name", "docente__last_name",
    )
    list_select_related = ("docente", "equipo")
    actions = ("enviar_recordatorio",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Estado")
    def estado_actual(self, prestamo):
        return prestamo.estado

    @admin.display(description="Días de retraso")
    def retraso(self, prestamo):
        return prestamo.dias_de_retraso

    def has_recordatorio_permission(self, request):
        return request.user.has_perm("prestamos.enviar_recordatorios")

    @admin.action(description="Enviar recordatorio de devolución", permissions=["recordatorio"])
    def enviar_recordatorio(self, request, queryset):
        correos = []
        for prestamo in queryset.activos().exclude(docente__email="").select_related("docente", "equipo"):
            correos.append((
                "Recordatorio de devolución de equipo",
                f"Equipo: {prestamo.equipo}\n"
                f"Unidades: {prestamo.cantidad}\n"
                f"Fecha prevista de devolución: {prestamo.fecha_devolucion:%d/%m/%Y}\n"
                "Coordina la entrega con el personal de laboratorio.",
                None,
                [prestamo.docente.email],
            ))
        if not correos:
            self.message_user(request, "No hay préstamos activos con correo en la selección.", messages.WARNING)
            return
        try:
            enviados = send_mass_mail(correos)
        except OSError:
            self.message_user(request, "No se pudo completar el envío de recordatorios.", messages.ERROR)
        else:
            self.message_user(request, f"Recordatorios enviados: {enviados}.")
