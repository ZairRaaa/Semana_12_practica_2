from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import NON_FIELD_ERRORS, PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_safe

from .eventos import registrar_evento
from .forms import DevolucionForm, RegistroPrestamoForm, SolicitudPrestamoForm
from .grupos import ASISTENTES
from .models import Equipo, Prestamo
from .servicios import registrar_devolucion


@require_safe
def catalogo(request):
    equipos = Equipo.objects.select_related("laboratorio").con_disponibilidad()
    busqueda = request.GET.get("q", "").strip()
    if busqueda:
        equipos = equipos.filter(
            Q(codigo_patrimonial__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
            | Q(categoria__icontains=busqueda)
        )
    return render(request, "prestamos/catalogo.html", {"equipos": equipos, "busqueda": busqueda})


def _registrar(request, formulario, destino, titulo):
    if request.method == "POST" and formulario.is_valid():
        try:
            prestamo = formulario.registrar()
        except ValidationError as error:
            for campo, errores in error.error_dict.items():
                formulario.add_error(None if campo == NON_FIELD_ERRORS else campo, errores)
        else:
            registrar_evento(request, "prestamo", prestamo_id=prestamo.pk)
            messages.success(request, "El préstamo quedó registrado.")
            return redirect(destino)
    return render(request, "prestamos/formulario.html", {"form": formulario, "titulo": titulo})


@login_required
@permission_required("prestamos.solicitar_prestamo", raise_exception=True)
@require_http_methods(["GET", "POST"])
def solicitar(request):
    datos = request.POST if request.method == "POST" else None
    formulario = SolicitudPrestamoForm(
        datos, docente=request.user, initial={"equipo": request.GET.get("equipo")}
    )
    return _registrar(request, formulario, "prestamos:historial", "Solicitar préstamo")


@login_required
@permission_required("prestamos.registrar_prestamo", raise_exception=True)
@require_http_methods(["GET", "POST"])
def registrar(request):
    datos = request.POST if request.method == "POST" else None
    return _registrar(
        request, RegistroPrestamoForm(datos), "prestamos:activos", "Registrar préstamo"
    )


@login_required
@permission_required("prestamos.ver_historial_propio", raise_exception=True)
@require_safe
def historial(request):
    prestamos = Prestamo.objects.filter(docente=request.user).select_related("equipo")
    return render(request, "prestamos/listado.html", {
        "prestamos": prestamos, "titulo": "Mis préstamos",
    })


def _verificar_asistente(user):
    if not user.groups.filter(name=ASISTENTES).exists():
        raise PermissionDenied


@login_required
@permission_required("prestamos.registrar_devolucion", raise_exception=True)
@require_safe
def activos(request):
    _verificar_asistente(request.user)
    prestamos = Prestamo.objects.activos().select_related("equipo", "docente")
    return render(request, "prestamos/listado.html", {
        "prestamos": prestamos, "titulo": "Préstamos por devolver", "gestionar": True,
    })


@login_required
@permission_required("prestamos.registrar_devolucion", raise_exception=True)
@require_http_methods(["GET", "POST"])
def devolver(request, prestamo_id):
    _verificar_asistente(request.user)
    prestamo = get_object_or_404(Prestamo.objects.select_related("equipo", "docente"), pk=prestamo_id)
    datos = request.POST if request.method == "POST" else None
    formulario = DevolucionForm(datos)
    if request.method == "POST" and formulario.is_valid():
        try:
            registrar_devolucion(prestamo, **formulario.cleaned_data)
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            registrar_evento(request, "devolucion", prestamo_id=prestamo.pk)
            messages.success(request, "La devolución quedó registrada.")
            return redirect("prestamos:activos")
    return render(request, "prestamos/formulario.html", {
        "form": formulario, "titulo": "Registrar devolución", "prestamo": prestamo,
    })
