from django import forms
from django.contrib.auth import get_user_model
from django.utils.html import strip_tags

from .grupos import DOCENTES
from .models import Equipo, Prestamo
from .servicios import registrar_prestamo, validar_solicitud


class SolicitudPrestamoForm(forms.ModelForm):
    cantidad = forms.IntegerField(min_value=1, initial=1)

    class Meta:
        model = Prestamo
        fields = ("equipo", "cantidad", "fecha_prestamo", "fecha_devolucion", "observaciones")
        widgets = {
            "fecha_prestamo": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "fecha_devolucion": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, docente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.docente = docente

    def clean_observaciones(self):
        return strip_tags(self.cleaned_data["observaciones"]).strip()

    def clean(self):
        datos = super().clean()
        validar_solicitud(
            docente=datos.get("docente", self.docente),
            equipo=datos.get("equipo"),
            cantidad=datos.get("cantidad"),
            fecha_prestamo=datos.get("fecha_prestamo"),
            fecha_devolucion=datos.get("fecha_devolucion"),
        )
        return datos

    def registrar(self):
        datos = self.cleaned_data.copy()
        datos.setdefault("docente", self.docente)
        return registrar_prestamo(**datos)


class RegistroPrestamoForm(SolicitudPrestamoForm):
    docente = forms.ModelChoiceField(queryset=get_user_model()._default_manager.none())

    class Meta(SolicitudPrestamoForm.Meta):
        fields = ("docente", *SolicitudPrestamoForm.Meta.fields)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["docente"].queryset = get_user_model()._default_manager.filter(
            is_active=True, groups__name=DOCENTES
        )


class DevolucionForm(forms.Form):
    estado_retorno = forms.ChoiceField(label="Estado al devolver", choices=Equipo.Estado.choices)
    observaciones_devolucion = forms.CharField(
        label="Observaciones de devolución", max_length=500, required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_observaciones_devolucion(self):
        return strip_tags(self.cleaned_data["observaciones_devolucion"]).strip()
