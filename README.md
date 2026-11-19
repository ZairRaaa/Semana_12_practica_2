# Préstamos de laboratorio · UNCP

Práctica grupal de Desarrollo de Aplicaciones Web. El portal usa Django 5.2, SQLite y la zona horaria de Lima.

## Puesta en marcha

Con Python 3.12 o posterior, ejecuta desde la raíz del repositorio en PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py configurar_roles
.\.venv\Scripts\python.exe manage.py cargar_prestamos_demo
.\.venv\Scripts\python.exe manage.py changepassword demo-lab-ana@uncp.edu.pe
.\.venv\Scripts\python.exe manage.py changepassword demo-lab-admin@uncp.edu.pe
.\.venv\Scripts\python.exe manage.py changepassword demo-lab-asistente@uncp.edu.pe
.\.venv\Scripts\python.exe manage.py runserver
```

Entra en http://127.0.0.1:8000/ con una de las cuentas de demostración. El correo funciona como nombre de usuario en cuentas locales de Django. El catálogo público está en `/prestamos/`. Como docente puedes solicitar y revisar tus préstamos. Como asistente puedes registrar préstamos a nombre de un docente y registrar devoluciones. El administrador usa `/admin/` para operar el catálogo y consultar los reportes.

Para verificar la separación de roles, abre `/auditoria/` como docente y luego como administrador. El docente recibe un 403. El administrador puede consultar el evento en el portal y en Django Admin. En DevTools, revisa la cookie `laboratorio_sesion` con `HttpOnly`, `SameSite=Lax` y vigencia de 30 minutos desde la última actividad. El cierre de sesión usa POST con CSRF.

Pruebas y verificación de migraciones:

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Para HTTPS, configura `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS`. En ese modo Django exige HTTPS y marca las cookies de sesión y CSRF con `Secure`.

## Evidencias y repositorios

La [guía de integración](prestamos/INTEGRACION.md) explica los permisos, los eventos de auditoría y las capturas de este caso.

- [Caso 2. Consultas médicas](https://github.com/taangel687-netizen/CASO-2---AGUILAR---ROJAS-Y-TOCAS-).
- [Caso 3. Asistencia y permisos](https://github.com/taangel687-netizen/CASO-3---AGUILAR---TOCAS---ROJAS).
