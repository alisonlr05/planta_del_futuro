"""Limpieza del dataset AI4I 2020: nombres en español, °C y validaciones."""

import pandas as pd

from planta.config import KELVIN_A_CELSIUS

# Nombres originales (inglés) -> nombres del contrato de datos (español snake_case).
NOMBRES_COLUMNAS: dict[str, str] = {
    "UID": "id_registro",
    "Product ID": "id_producto",
    "Type": "tipo_producto",
    "Air temperature": "temperatura_aire_c",
    "Process temperature": "temperatura_proceso_c",
    "Rotational speed": "velocidad_rotacion_rpm",
    "Torque": "torque_nm",
    "Tool wear": "desgaste_herramienta_min",
    "Machine failure": "falla_maquina",
    "TWF": "falla_desgaste_herramienta",  # Tool Wear Failure
    "HDF": "falla_disipacion_calor",  # Heat Dissipation Failure
    "PWF": "falla_potencia",  # Power Failure
    "OSF": "falla_sobreesfuerzo",  # Overstrain Failure
    "RNF": "falla_aleatoria",  # Random Failure
}

COLUMNAS_TEMPERATURA: list[str] = ["temperatura_aire_c", "temperatura_proceso_c"]
DECIMALES_TEMPERATURA: int = 2


def renombrar_columnas(datos: pd.DataFrame) -> pd.DataFrame:
    """Renombra las columnas a español; falla si falta alguna columna esperada."""
    return datos.rename(columns=NOMBRES_COLUMNAS, errors="raise")


def kelvin_a_celsius(datos: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Convierte de Kelvin a grados Celsius las columnas indicadas."""
    datos = datos.copy()
    datos[columnas] = (datos[columnas] - KELVIN_A_CELSIUS).round(DECIMALES_TEMPERATURA)
    return datos


def validar_sin_nulos(datos: pd.DataFrame) -> None:
    """Lanza un error si alguna columna tiene valores vacíos."""
    nulos_por_columna = datos.isna().sum()
    columnas_con_nulos = nulos_por_columna[nulos_por_columna > 0]
    if not columnas_con_nulos.empty:
        raise ValueError(f"Hay valores nulos:\n{columnas_con_nulos}")


def validar_sin_duplicados(datos: pd.DataFrame, columna_id: str = "id_registro") -> None:
    """Lanza un error si hay filas repetidas o identificadores repetidos."""
    filas_duplicadas = int(datos.duplicated().sum())
    ids_duplicados = int(datos[columna_id].duplicated().sum())
    if filas_duplicadas or ids_duplicados:
        raise ValueError(
            f"Hay {filas_duplicadas} filas duplicadas y {ids_duplicados} '{columna_id}' repetidos."
        )


def limpiar_dataset(datos: pd.DataFrame) -> pd.DataFrame:
    """Aplica todos los pasos de limpieza y devuelve el dataset validado."""
    limpios = renombrar_columnas(datos)
    limpios = kelvin_a_celsius(limpios, COLUMNAS_TEMPERATURA)
    validar_sin_nulos(limpios)
    validar_sin_duplicados(limpios)
    return limpios
