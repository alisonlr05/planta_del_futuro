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
RUTA_CSV_OEE: Path = DIR_DATOS_PROCESADOS / "oee_turnos.csv"
RUTA_CSV_PREDICCIONES: Path = DIR_DATOS_PROCESADOS / "predicciones_fallas.csv"
RUTA_CSV_ALERTAS: Path = DIR_DATOS_PROCESADOS / "alertas_por_turno.csv"

# Tablas extra para el modelo estrella de Power BI.
RUTA_CSV_ALERTAS_DETALLE: Path = DIR_DATOS_PROCESADOS / "alertas_detalle.csv"
RUTA_CSV_DIM_MAQUINAS: Path = DIR_DATOS_PROCESADOS / "dim_maquinas.csv"
RUTA_CSV_DIM_TURNOS: Path = DIR_DATOS_PROCESADOS / "dim_turnos.csv"
RUTA_CSV_DIM_FECHAS: Path = DIR_DATOS_PROCESADOS / "dim_fechas.csv"

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

# Hora en que empieza la jornada: los ciclos antes de esta hora (00:00-05:59)
# pertenecen al turno Noche del día anterior.
HORA_INICIO_JORNADA: int = 6

# --- OEE (supuestos: el dataset no trae tiempos de paro) --------------------
MINUTOS_REPARACION_FALLA: int = 20  # paro por cada ciclo con falla de máquina
MINUTOS_CAMBIO_HERRAMIENTA: int = 5  # paro por cada cambio de herramienta
VELOCIDAD_NOMINAL_RPM: int = 1500  # velocidad ideal (≈ mediana real del dataset)

# --- Modelo de predicción de fallas ------------------------------------------
PROPORCION_PRUEBA: float = 0.2  # 20 % de los ciclos se reserva para evaluar el modelo

# Niveles de riesgo según la probabilidad de falla que da el modelo.
UMBRAL_RIESGO_MEDIO: float = 0.30  # desde 30 % -> "Medio"
UMBRAL_RIESGO_ALTO: float = 0.60  # desde 60 % -> "Alto" (n8n enviará alerta)

# --- Alertas (n8n envía un correo por turno con alertas) ---------------------
NIVEL_RIESGO_ALERTA: str = "Alto"  # solo los ciclos con este nivel generan alerta

# Señales para explicar la causa probable de una alerta.
# Límites tomados de la documentación del dataset AI4I 2020.
DIFERENCIA_TEMPERATURA_MINIMA_C: float = 8.6  # menos que esto: el calor no se disipa...
VELOCIDAD_MINIMA_DISIPACION_RPM: int = 1380  # ...si además la velocidad es baja
POTENCIA_MINIMA_W: int = 3500
POTENCIA_MAXIMA_W: int = 9000
LIMITE_ESFUERZO_NM_MIN: dict[str, int] = {"L": 11000, "M": 12000, "H": 13000}  # por tipo de producto
DESGASTE_CAMBIO_HERRAMIENTA_MIN: int = 200  # desde aquí conviene cambiar la herramienta

# --- Conversión de unidades --------------------------------------------------
KELVIN_A_CELSIUS: float = 273.15

# --- Contrato de datos de los CSV de salida ----------------------------------
CODIFICACION_CSV: str = "utf-8"
SEPARADOR_CSV: str = ","
FORMATO_FECHA_HORA: str = "%Y-%m-%dT%H:%M:%S"  # ISO 8601
