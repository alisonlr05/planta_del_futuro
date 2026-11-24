"""Tablas de dimensiones para el modelo estrella de Power BI.

Las tablas de hechos (OEE, predicciones, alertas) se conectan con estas
dimensiones. Así un solo filtro de máquina, turno o fecha afecta a todas
las páginas del dashboard, y los turnos y meses se ordenan bien.
"""

import pandas as pd

from planta.config import IDS_MAQUINAS, TURNOS

# Nombres en español fijos (no dependen del idioma de la computadora).
NOMBRES_MESES: list[str] = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
NOMBRES_DIAS: list[str] = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIA_INICIO_FIN_DE_SEMANA: int = 5  # sábado (lunes = 0)


def crear_dim_maquinas(ids_maquinas: list[str] = IDS_MAQUINAS) -> pd.DataFrame:
    """Una fila por máquina: id (M01) y nombre para mostrar (Máquina 01)."""
    return pd.DataFrame(
        {
            "id_maquina": ids_maquinas,
            "nombre_maquina": [f"Máquina {id_maquina[1:]}" for id_maquina in ids_maquinas],
        }
    )


def crear_dim_turnos(turnos: dict[str, tuple[int, int]] = TURNOS) -> pd.DataFrame:
    """Una fila por turno, con su orden (1, 2, 3) y su horario (06:00-14:00)."""
    filas = [
        {
            "turno": nombre,
            "orden_turno": orden,
            "hora_inicio": inicio,
            "hora_fin": fin,
            "horario": f"{inicio:02d}:00-{fin:02d}:00",
        }
        for orden, (nombre, (inicio, fin)) in enumerate(turnos.items(), start=1)
    ]
    return pd.DataFrame(filas)


def crear_dim_fechas(fecha_inicio: pd.Timestamp, fecha_fin: pd.Timestamp) -> pd.DataFrame:
    """Calendario con un día por fila, entre dos fechas (ambas incluidas)."""
    fechas = pd.date_range(pd.Timestamp(fecha_inicio).normalize(), pd.Timestamp(fecha_fin).normalize())
    return pd.DataFrame(
        {
            "fecha": fechas,
            "anio": fechas.year,
            "mes_numero": fechas.month,
            "mes_nombre": [NOMBRES_MESES[mes - 1] for mes in fechas.month],
            "semana_iso": fechas.isocalendar().week.to_numpy(),
            "dia_semana_numero": fechas.day_of_week + 1,  # lunes = 1 ... domingo = 7
            "dia_semana_nombre": [NOMBRES_DIAS[dia] for dia in fechas.day_of_week],
            "es_fin_de_semana": (fechas.day_of_week >= DIA_INICIO_FIN_DE_SEMANA).astype(int),
        }
    )


def crear_dim_fechas_desde_datos(fechas: pd.Series) -> pd.DataFrame:
    """Calendario que cubre desde la primera hasta la última fecha de los datos."""
    fechas = pd.to_datetime(fechas)
    return crear_dim_fechas(fechas.min(), fechas.max())
