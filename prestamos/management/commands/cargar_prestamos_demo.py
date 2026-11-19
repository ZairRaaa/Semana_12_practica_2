from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from prestamos.grupos import ADMINISTRADORES, ASISTENTES, DOCENTES
from prestamos.models import Equipo, Laboratorio, Prestamo


EQUIPOS = (
    ("Laptop de laboratorio", "Lenovo", "ThinkPad E14", "Cómputo", Equipo.Estado.OPERATIVO),
    ("Proyector portátil", "Epson", "PowerLite X49", "Proyección", Equipo.Estado.OPERATIVO),
    ("Cámara digital", "Canon", "EOS 2000D", "Audiovisual", Equipo.Estado.OPERATIVO),
    ("Kit de Arduino", "Arduino", "Uno R3", "Electrónica", Equipo.Estado.OPERATIVO),
    ("Router inalámbrico", "TP-Link", "Archer C80", "Redes", Equipo.Estado.OPERATIVO),
    ("Switch administrable", "Cisco", "CBS250", "Redes", Equipo.Estado.OPERATIVO),
    ("Laptop de simulación", "Dell", "Latitude 5440", "Cómputo", Equipo.Estado.OPERATIVO),
    ("Proyector de aula", "BenQ", "MW560", "Proyección", Equipo.Estado.MANTENIMIENTO),
    ("Cámara web", "Logitech", "C920", "Audiovisual", Equipo.Estado.MANTENIMIENTO),
    ("Switch de diagnóstico", "D-Link", "DGS-1100", "Redes", Equipo.Estado.BAJA),
)


def crear_usuario(nombre, grupo, nombres, apellidos):
    correo = f"{nombre}@{settings.CASO.dominio}"
    usuario, creado = get_user_model()._default_manager.get_or_create(
        username=correo,
        defaults={
            "first_name": nombres,
            "last_name": apellidos,
            "email": f"{nombre}@example.test",
            "is_staff": grupo.name == ADMINISTRADORES,
        },
    )
    if creado:
        usuario.set_unusable_password()
        usuario.save(update_fields=("password",))
    usuario.groups.add(grupo)
    return usuario


class Command(BaseCommand):
    help = "Carga 10 equipos, 5 usuarios ficticios y 15 préstamos de demostración."

    @transaction.atomic
    def handle(self, *args, **options):
        grupos = {
            nombre: Group.objects.get_or_create(name=nombre)[0]
            for nombre in (ADMINISTRADORES, ASISTENTES, DOCENTES)
        }
        crear_usuario("demo-lab-admin", grupos[ADMINISTRADORES], "Marta", "Campos")
        crear_usuario("demo-lab-asistente", grupos[ASISTENTES], "Luis", "Vega")
        docentes = [
            crear_usuario("demo-lab-ana", grupos[DOCENTES], "Ana", "Quispe"),
            crear_usuario("demo-lab-jorge", grupos[DOCENTES], "Jorge", "Salas"),
            crear_usuario("demo-lab-elena", grupos[DOCENTES], "Elena", "Paredes"),
        ]

        laboratorios = [
            Laboratorio.objects.get_or_create(nombre=f"Laboratorio {numero}")[0]
            for numero in range(1, 6)
        ]
        hoy = timezone.localdate()
        equipos = []
        for indice, (nombre, marca, modelo, categoria, estado) in enumerate(EQUIPOS):
            equipo, _ = Equipo.objects.get_or_create(
                codigo_patrimonial=f"DEMO-LAB-{indice + 1:03d}",
                defaults={
                    "nombre": nombre, "marca": marca, "modelo": modelo, "categoria": categoria,
                    "estado": estado, "stock_total": 3, "laboratorio": laboratorios[indice % 5],
                    "ultimo_mantenimiento": hoy - timedelta(days=7 + indice),
                },
            )
            equipos.append(equipo)

        for indice, docente in enumerate(docentes):
            for orden in range(5):
                if orden < 2:
                    equipo = equipos[indice * 2 + orden]
                    dias_inicio, dias_entrega = (8, -2) if orden == 0 else (1, 3)
                    devuelto_en = None
                else:
                    equipo = equipos[(indice * 2 + orden) % len(equipos)]
                    dias_inicio, dias_entrega = 14 + orden, -9 - orden
                    devuelto_en = timezone.now() - timedelta(days=9 + orden)

                Prestamo.objects.get_or_create(
                    docente=docente, equipo=equipo,
                    defaults={
                        "cantidad": 1,
                        "fecha_prestamo": hoy - timedelta(days=dias_inicio),
                        "fecha_devolucion": hoy + timedelta(days=dias_entrega),
                        "observaciones": "Préstamo de demostración.",
                        "devuelto_en": devuelto_en,
                        "estado_retorno": Equipo.Estado.OPERATIVO if devuelto_en else "",
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            "Datos de demostración listos. Usa changepassword para habilitar el acceso a una cuenta."
        ))
