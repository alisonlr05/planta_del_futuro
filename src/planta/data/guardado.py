"""Guardado de los CSV de data/processed/ según el contrato de datos."""

from pathlib import Path

import pandas as pd

from planta.config import CODIFICACION_CSV, FORMATO_FECHA_HORA, RUTA_CSV_PRODUCCION, SEPARADOR_CSV


def formatear_columnas_fecha(datos: pd.DataFrame) -> pd.DataFrame:
    """Convierte las columnas de fecha a texto ISO 8601 (ej. 2026-09-01T06:00:00)."""
    datos = datos.copy()
    for columna in datos.select_dtypes(include="datetime").columns:
        datos[columna] = datos[columna].dt.strftime(FORMATO_FECHA_HORA)
    return datos


def guardar_csv_procesado(datos: pd.DataFrame, ruta: Path = RUTA_CSV_PRODUCCION) -> Path:
    """Guarda el CSV en UTF-8, separado por comas y con fechas ISO 8601."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    formatear_columnas_fecha(datos).to_csv(
        ruta, index=False, sep=SEPARADOR_CSV, encoding=CODIFICACION_CSV
    )
    return ruta
