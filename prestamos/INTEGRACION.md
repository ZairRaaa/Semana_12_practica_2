# Integración de préstamos

- Añadir `prestamos.apps.PrestamosConfig` a `INSTALLED_APPS` y montar `include("prestamos.urls")` en el catálogo. Las vistas protegidas usan `LOGIN_URL`. La app usa `AUTH_USER_MODEL` en sus relaciones y espera los campos estándar de usuario de Django para la búsqueda de docentes y los datos de prueba.
- Ejecutar `python manage.py migrate` antes de asignar permisos. Los nombres de grupos definidos en `prestamos/grupos.py` se usan también para elegir docentes y limitar las devoluciones a asistentes.

| Grupo | Permisos de este módulo |
| --- | --- |
| Administradores | Permisos CRUD de `Equipo` y `Laboratorio`, `view_prestamo`, `enviar_recordatorios`. La cuenta requiere acceso al Admin. |
| Docentes | `solicitar_prestamo`, `ver_historial_propio`. |
| Asistentes | `registrar_prestamo`, `registrar_devolucion`. |

Los permisos pertenecen a la aplicación `prestamos`. El catálogo permite acceso anónimo. Si un equipo tiene historial, se puede dar de baja para conservar la trazabilidad de sus préstamos.

El middleware puede leer `request.eventos_prestamos` después de procesar la respuesta. Cada entrada incluye `accion` y el identificador correspondiente. `prestamo` y `devolucion` incluyen `prestamo_id`. `eliminacion` incluye `equipo_id`. Para la alerta al iniciar sesión, consultar `Prestamo.objects.vencidos().filter(docente=usuario)`.

El Admin usa el backend de correo configurado en el proyecto para enviar recordatorios. Para probar el envío en local se puede configurar el backend de consola.

## Datos de prueba

Ejecutar `python manage.py cargar_prestamos_demo`. El comando puede repetirse sobre la misma base y las cuentas nuevas se crean sin contraseña. Asignar los permisos de la tabla con el sistema de grupos del proyecto y usar `python manage.py changepassword <usuario>` en las cuentas que se quieran usar para la demostración.

- Administradora: `demo_lab_admin`
- Asistente: `demo_lab_asistente`
- Docentes: `demo_lab_ana`, `demo_lab_jorge` y `demo_lab_elena`

Como ejemplo de validación en pantalla, solicitar cuatro unidades de un equipo operativo de demostración. Para un préstamo válido, elegir un equipo con unidades disponibles y una fecha de devolución posterior.
