"""Configuración central del proyecto: rutas, semilla y parámetros de simulación.

Todos los valores "fijos" del proyecto viven aquí para no repetir números
sueltos (valores mágicos) en el resto del código.
"""

from pathlib import Path

# --- Rutas -------------------------------------------------------------------
# config.py está en src/planta/, así que la raíz del proyecto está dos niveles arriba.
RAIZ_PROYECTO: Path = Path(__file__).resolve().parents[2]

DIR_DATOS: Path = RAIZ_PROYECTO / "data"
DIR_DATOS_CRUDOS: Path = DIR_DATOS / "raw"
DIR_DATOS_PROCESADOS: Path = DIR_DATOS / "processed"

RUTA_DATASET_CRUDO: Path = DIR_DATOS_CRUDOS / "ai4i2020.csv"
RUTA_CSV_PRODUCCION: Path = DIR_DATOS_PROCESADOS / "produccion_planta.csv"

# --- Dataset -----------------------------------------------------------------
ID_DATASET_UCI: int = 601  # AI4I 2020 Predictive Maintenance Dataset

# --- Reproducibilidad --------------------------------------------------------
SEMILLA_REPRODUCIBLE: int = 42  # fija el azar para que los resultados se puedan repetir

# --- Simulación de la planta -------------------------------------------------
CANTIDAD_MAQUINAS: int = 5
IDS_MAQUINAS: list[str] = [f"M{i:02d}" for i in range(1, CANTIDAD_MAQUINAS + 1)]  # M01..M05

MINUTOS_CICLO: int = 30  # cada máquina registra un ciclo cada 30 minutos
INICIO_SIMULACION: str = "2026-09-01 06:00:00"  # inicia con el turno Mañana

# Turnos: nombre -> (hora de inicio, hora de fin). Noche cruza la medianoche.
TURNOS: dict[str, tuple[int, int]] = {
    "Mañana": (6, 14),
    "Tarde": (14, 22),
    "Noche": (22, 6),
}

# --- Conversión de unidades --------------------------------------------------
KELVIN_A_CELSIUS: float = 273.15

# --- Contrato de datos de los CSV de salida ----------------------------------
CODIFICACION_CSV: str = "utf-8"
SEPARADOR_CSV: str = ","
FORMATO_FECHA_HORA: str = "%Y-%m-%dT%H:%M:%S"  # ISO 8601
