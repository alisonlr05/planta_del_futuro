"""Variables derivadas para el modelo de predicción de fallas.

Combinan las mediciones de los sensores en magnitudes físicas que explican
mejor las causas de falla vistas en el análisis exploratorio.
"""

import math

import pandas as pd

RPM_A_RADIANES_POR_SEGUNDO: float = 2 * math.pi / 60  # 1 rpm = 2π/60 rad/s

COLUMNAS_DERIVADAS: list[str] = ["diferencia_temperatura_c", "potencia_w", "esfuerzo_nm_min"]


def calcular_diferencia_temperatura(datos: pd.DataFrame) -> pd.Series:
    """Proceso − aire (°C). Si es pequeña, el calor no se disipa (falla HDF)."""
    return (datos["temperatura_proceso_c"] - datos["temperatura_aire_c"]).round(2)


def calcular_potencia(datos: pd.DataFrame) -> pd.Series:
    """Potencia mecánica (W) = torque × velocidad angular. Fuera de rango -> falla PWF."""
    velocidad_angular = datos["velocidad_rotacion_rpm"] * RPM_A_RADIANES_POR_SEGUNDO
    return (datos["torque_nm"] * velocidad_angular).round(1)


def calcular_esfuerzo(datos: pd.DataFrame) -> pd.Series:
    """Esfuerzo acumulado (Nm·min) = desgaste × torque. Muy alto -> falla OSF."""
    return (datos["desgaste_herramienta_min"] * datos["torque_nm"]).round(1)


def agregar_variables_derivadas(datos: pd.DataFrame) -> pd.DataFrame:
    """Agrega las tres variables derivadas al final de la tabla."""
    datos = datos.copy()
    datos["diferencia_temperatura_c"] = calcular_diferencia_temperatura(datos)
    datos["potencia_w"] = calcular_potencia(datos)
    datos["esfuerzo_nm_min"] = calcular_esfuerzo(datos)
    return datos
