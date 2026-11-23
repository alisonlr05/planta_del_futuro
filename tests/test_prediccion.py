"""Pruebas de las variables derivadas y del modelo de predicción de fallas."""

import math

import numpy as np
import pandas as pd
import pytest

from planta.features.variables import agregar_variables_derivadas
from planta.models.prediccion import (
    clasificar_riesgo,
    construir_tabla_predicciones,
    crear_random_forest,
    dividir_datos,
    preparar_variables,
)

COLUMNAS_TIPO_FALLA = [
    "falla_desgaste_herramienta",
    "falla_disipacion_calor",
    "falla_potencia",
    "falla_sobreesfuerzo",
    "falla_aleatoria",
]


def crear_ciclos_sinteticos(cantidad: int = 200, semilla: int = 0) -> pd.DataFrame:
    """Ciclos inventados con las mismas columnas que produccion_planta.csv."""
    azar = np.random.default_rng(semilla)
    datos = pd.DataFrame({
        "id_registro": range(1, cantidad + 1),
        "id_maquina": "M01",
        "fecha_hora": pd.date_range("2026-09-01 06:00", periods=cantidad, freq="30min"),
        "turno": "Mañana",
        "tipo_producto": azar.choice(["L", "M", "H"], cantidad),
        "temperatura_aire_c": azar.normal(27, 2, cantidad).round(2),
        "temperatura_proceso_c": azar.normal(37, 1.5, cantidad).round(2),
        "velocidad_rotacion_rpm": azar.integers(1200, 2800, cantidad),
        "torque_nm": azar.normal(40, 10, cantidad).round(1),
        "desgaste_herramienta_min": azar.integers(0, 250, cantidad),
    })
    # Regla simple: falla si el torque es muy alto (≈ 10 % de los ciclos).
    datos["falla_maquina"] = (datos["torque_nm"] > 53).astype(int)
    for columna in COLUMNAS_TIPO_FALLA:
        datos[columna] = 0
    return datos


# --- Variables derivadas --------------------------------------------------------
def test_variables_derivadas_calculadas_a_mano() -> None:
    datos = pd.DataFrame({
        "temperatura_aire_c": [25.0],
        "temperatura_proceso_c": [35.5],
        "velocidad_rotacion_rpm": [60],  # 60 rpm = 1 vuelta/s = 2π rad/s
        "torque_nm": [10.0],
        "desgaste_herramienta_min": [200],
    })
    fila = agregar_variables_derivadas(datos).iloc[0]
    assert fila["diferencia_temperatura_c"] == pytest.approx(10.5)
    assert fila["potencia_w"] == pytest.approx(round(10 * 2 * math.pi, 1))  # 62.8 W
    assert fila["esfuerzo_nm_min"] == pytest.approx(2000.0)


# --- Niveles de riesgo ------------------------------------------------------------
@pytest.mark.parametrize(
    ("probabilidad", "nivel"),
    [
        (0.0, "Bajo"),
        (0.29, "Bajo"),
        (0.30, "Medio"),  # el límite pertenece al nivel superior
        (0.59, "Medio"),
        (0.60, "Alto"),
        (1.0, "Alto"),
    ],
)
def test_clasificar_riesgo_respeta_los_umbrales(probabilidad: float, nivel: str) -> None:
    resultado = clasificar_riesgo(np.array([probabilidad]), umbral_medio=0.30, umbral_alto=0.60)
    assert resultado.iloc[0] == nivel


# --- Preparación de datos ---------------------------------------------------------
def test_preparar_variables_no_usa_columnas_de_tipo_de_falla() -> None:
    entradas, objetivo = preparar_variables(crear_ciclos_sinteticos())
    columnas_prohibidas = set(COLUMNAS_TIPO_FALLA) | {"falla_maquina", "id_registro", "id_maquina"}
    assert columnas_prohibidas.isdisjoint(entradas.columns)
    assert objetivo.name == "falla_maquina"


def test_dividir_datos_mantiene_la_proporcion_de_fallas() -> None:
    entradas, objetivo = preparar_variables(crear_ciclos_sinteticos(cantidad=500))
    _, _, objetivo_entrenamiento, objetivo_prueba = dividir_datos(
        entradas, objetivo, proporcion_prueba=0.2, semilla=42
    )
    assert len(objetivo_prueba) == 100
    assert objetivo_prueba.mean() == pytest.approx(objetivo_entrenamiento.mean(), abs=0.01)


# --- Modelo -----------------------------------------------------------------------
def test_random_forest_es_reproducible_con_la_misma_semilla() -> None:
    entradas, objetivo = preparar_variables(crear_ciclos_sinteticos())
    probabilidades_1 = crear_random_forest(semilla=42).fit(entradas, objetivo).predict_proba(entradas)
    probabilidades_2 = crear_random_forest(semilla=42).fit(entradas, objetivo).predict_proba(entradas)
    assert np.array_equal(probabilidades_1, probabilidades_2)


def test_tabla_de_predicciones_tiene_el_contrato_de_datos() -> None:
    datos = crear_ciclos_sinteticos(cantidad=3)
    tabla = construir_tabla_predicciones(datos, np.array([0.1, 0.45, 0.9]))
    assert list(tabla.columns) == [
        "id_registro", "id_maquina", "fecha_hora", "turno", "tipo_producto",
        "probabilidad_falla", "nivel_riesgo", "falla_real",
    ]
    assert tabla["nivel_riesgo"].tolist() == ["Bajo", "Medio", "Alto"]
