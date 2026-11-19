from dataclasses import dataclass


@dataclass(frozen=True)
class Caso:
    titulo: str
    institucion: str
    dominio: str
    minutos: int
    roles: dict


CASOS = {
    "laboratorio": Caso(
        "Préstamos de laboratorio", "Facultad de Ingeniería de Sistemas · UNCP",
        "uncp.edu.pe", 30,
        {"admin": "Administrador", "docente": "Docente", "asistente": "Asistente"},
    ),
    "consultas": Caso(
        "Consultas médicas", "Centro Médico Universitario · UNCP", "uncp.edu.pe", 20,
        {"admin": "Admins", "medico": "Médicos", "recepcionista": "Recepcionistas",
         "paciente": "Pacientes"},
    ),
    "asistencia": Caso(
        "Asistencia y permisos", "TecnoAndes S.A.C.", "tecnoandes.pe", 45,
        {"rrhh": "RRHH", "jefe": "Jefes de área", "empleado": "Empleados",
         "contador": "Contadores"},
    ),
}
