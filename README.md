# Préstamos de laboratorio · UNCP

Práctica grupal de Desarrollo de Aplicaciones Web. El portal usa Django 5.2, SQLite y la zona horaria de Lima.

## Puesta en marcha

Con Python 3.12 o posterior, ejecuta desde la raíz del repositorio en PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py configurar_roles
.\.venv\Scripts\python.exe manage.py cuenta_prueba demo-docente docente
.\.venv\Scripts\python.exe manage.py cuenta_prueba demo-admin admin
.\.venv\Scripts\python.exe manage.py cuenta_prueba demo-asistente asistente
.\.venv\Scripts\python.exe manage.py runserver
```

El comando solicita una contraseña temporal por cuenta. Entra en http://127.0.0.1:8000/ con el alias seguido de `@uncp.edu.pe`. El correo funciona como nombre de usuario en cuentas locales de Django. Usa identidades ficticias para la práctica. El portal no se conecta a un proveedor institucional.

Para verificar la separación de roles, abre `/auditoria/` como docente y luego como administrador. El docente recibe un 403. El administrador puede consultar el evento en el portal y en Django Admin. En DevTools, revisa la cookie `laboratorio_sesion` con `HttpOnly`, `SameSite=Lax` y vigencia de 30 minutos desde la última actividad. El cierre de sesión usa POST con CSRF.

Pruebas y verificación de migraciones:

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Para HTTPS, configura `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS`. En ese modo Django exige HTTPS y marca las cookies de sesión y CSRF con `Secure`.

## Integración con préstamos

| Operación | Regla para la vista o acción de Admin |
| --- | --- |
| Catálogo | Vista pública de lectura. Usa la ruta con nombre `catalogo` para mostrar el enlace en portada. |
| Solicitud | `@requiere_rol("docente", "asistente")`. El docente queda vinculado a `request.user`; el asistente puede registrar a nombre del docente seleccionado. |
| Historial | `historial_prestamos(request.user, queryset)` limita el queryset al docente autenticado. Usa ese queryset también para abrir un préstamo por ID. |
| Devolución | `@requiere_rol("asistente")`, método POST y una comprobación equivalente para cualquier acción de Admin. |
| Eliminación de equipo | `@requiere_rol("admin")`, método POST y permiso de eliminación restringido a Administrador en Django Admin. |
| Auditoría | Llama `auditar_operacion(request, "prestamo_creado", "prestamo", prestamo.pk)` dentro de la transacción que guarda el cambio. Usa `devolucion_registrada` y `equipo_eliminado` para las otras operaciones. |
| Vencimientos | Configura `DJANGO_AVISOS_INGRESO` con la ruta importable de una función `avisos(usuario, ahora)`. Pásale a `cuentas.avisos.prestamos_vencidos` el queryset de préstamos activos y la fecha local. El middleware muestra el resultado después de un ingreso correcto. |

Los grupos se crean con `configurar_roles`. Cuando existan las migraciones del dominio, define `PERMISOS_GRUPOS` en `config/settings.py` con permisos en formato `app.modelo.codename`, ejecuta el comando otra vez y aplica las mismas reglas en las vistas y acciones de Admin. Los usuarios de la carga deben tener como `username` su correo en minúsculas. El nombre del comando que carga equipos y préstamos se añadirá cuando se integre la carga del dominio.

## Reutilización en los otros casos

`DJANGO_CASO=consultas` activa los grupos médicos y una sesión de 20 minutos. `DJANGO_CASO=asistencia` activa los grupos de TecnoAndes y una sesión de 45 minutos. Cada perfil usa su propia base SQLite y cookie.

- **Consultas.** Pacientes agendan y cancelan sus propias citas y consultan su historial. Recepción agenda y cancela. Médicos cancelan y acceden a historiales. Administradores generan reportes. Aplica `historial_clinico` antes de cargar o mostrar un historial y registra `historial_consultado` con su ID, sin guardar contenido clínico. Usa `@controla_horario` con una función que valide la fecha y hora de la cita para POST. El aviso de ingreso recibe el queryset de citas pendientes del médico autenticado.
- **Asistencia.** El empleado registra su asistencia y solicita permisos. El jefe aprueba o consulta reportes en su área. RRHH puede aprobar cualquier solicitud y es el único grupo que corrige asistencia. Contabilidad consulta reportes globales por GET o HEAD. Las áreas, el dueño y el horario del turno se obtienen de objetos cargados en el servidor. Usa `@controla_horario` con un validador que llame a `validar_marcacion` para la entrada o salida correspondiente. Para el recordatorio, pasa el turno del día laborable y el estado de la marcación a `entrada_pendiente`.
