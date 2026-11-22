"""Carga del dataset AI4I 2020 con una copia local en data/raw/."""

from pathlib import Path

import pandas as pd
from ucimlrepo import fetch_ucirepo

from planta.config import ID_DATASET_UCI, RUTA_DATASET_CRUDO


def descargar_dataset(id_dataset: int = ID_DATASET_UCI) -> pd.DataFrame:
    """Descarga el dataset desde el repositorio UCI con todas sus columnas originales."""
    dataset = fetch_ucirepo(id=id_dataset)
    return dataset.data.original


def guardar_copia_cruda(datos: pd.DataFrame, ruta: Path = RUTA_DATASET_CRUDO) -> None:
    """Guarda una copia sin modificar del dataset en data/raw/."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos.to_csv(ruta, index=False)


def cargar_dataset_crudo(
    ruta: Path = RUTA_DATASET_CRUDO, forzar_descarga: bool = False
) -> pd.DataFrame:
    """Lee la copia local; si no existe (o se pide), la descarga y la guarda primero."""
    if forzar_descarga or not ruta.exists():
        guardar_copia_cruda(descargar_dataset(), ruta)
    return pd.read_csv(ruta)
