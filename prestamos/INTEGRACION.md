# Integración de préstamos

- La configuración del caso laboratorio instala la aplicación y publica el catálogo en `/prestamos/`. Las vistas protegidas usan el login de `cuentas`.
- Ejecutar `python manage.py migrate` y después `python manage.py configurar_roles`. Los grupos se usan para elegir docentes y limitar las devoluciones a asistentes.

| Grupo | Permisos de este módulo |
| --- | --- |
| Administrador | Permisos CRUD de `Equipo` y `Laboratorio`, `view_prestamo`, `enviar_recordatorios`. La cuenta requiere acceso al Admin. |
| Docente | `solicitar_prestamo`, `ver_historial_propio`. |
| Asistente | `registrar_prestamo`, `registrar_devolucion`. |

Los permisos pertenecen a la aplicación `prestamos`. El catálogo permite acceso anónimo. Si un equipo tiene historial, se puede dar de baja para conservar la trazabilidad de sus préstamos.

Las operaciones críticas registran en la misma transacción los eventos `prestamo_creado`, `devolucion_registrada` y `equipo_eliminado`. El middleware muestra un aviso tras el inicio de sesión si el docente tiene préstamos activos vencidos.

El Admin usa el backend de correo configurado en el proyecto para enviar recordatorios. Para probar el envío en local se puede configurar el backend de consola.

## Datos de prueba

Ejecutar `python manage.py cargar_prestamos_demo`. El comando puede repetirse sobre la misma base y las cuentas nuevas se crean sin contraseña. Usar `python manage.py changepassword <usuario>` en las cuentas que se quieran usar para la demostración.

- Administradora `demo-lab-admin@uncp.edu.pe`.
- Asistente `demo-lab-asistente@uncp.edu.pe`.
- Docentes `demo-lab-ana@uncp.edu.pe`, `demo-lab-jorge@uncp.edu.pe` y `demo-lab-elena@uncp.edu.pe`.

Como ejemplo de validación en pantalla, solicitar cuatro unidades de un equipo operativo de demostración. Para un préstamo válido, elegir un equipo con unidades disponibles y una fecha de devolución posterior.

## Evidencias del caso 1

- [Solicitud inválida](../evidencias/rojas/01-solicitud-invalida.png). El formulario rechaza cuatro unidades cuando solo hay tres disponibles.
- [Solicitud válida](../evidencias/rojas/02-solicitud-valida.png). Al corregir la cantidad, el préstamo queda registrado y aparece en el historial del docente.
- [Django Admin](../evidencias/rojas/03-admin-filtro-y-accion.png). El filtro muestra los préstamos vencidos, los días de retraso y la acción para enviar un recordatorio.
