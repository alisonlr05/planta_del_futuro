"""Modelo de predicción de fallas de máquina.

Flujo: preparar variables -> dividir entrenamiento/prueba -> entrenar ->
evaluar -> convertir la probabilidad de falla en un nivel de riesgo.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from planta.config import (
    PROPORCION_PRUEBA,
    SEMILLA_REPRODUCIBLE,
    UMBRAL_RIESGO_ALTO,
    UMBRAL_RIESGO_MEDIO,
)
from planta.features.variables import COLUMNAS_DERIVADAS, agregar_variables_derivadas

COLUMNA_OBJETIVO: str = "falla_maquina"
VARIABLES_NUMERICAS: list[str] = [
    "temperatura_aire_c",
    "temperatura_proceso_c",
    "velocidad_rotacion_rpm",
    "torque_nm",
    "desgaste_herramienta_min",
    *COLUMNAS_DERIVADAS,
]
VARIABLES_CATEGORICAS: list[str] = ["tipo_producto"]

# Las columnas de tipo de falla (TWF, HDF, ...) NO se usan: solo se conocen
# después de que la máquina falla (sería fuga de datos).

CANTIDAD_ARBOLES: int = 300
MAX_ITERACIONES_LOGISTICA: int = 1000
UMBRAL_DECISION: float = 0.5  # probabilidad desde la cual se predice "falla"
PLIEGUES_VALIDACION: int = 5
NIVELES_RIESGO: list[str] = ["Bajo", "Medio", "Alto"]


# --- Datos ------------------------------------------------------------------------
def preparar_variables(datos: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Separa las variables de entrada (X) y la variable a predecir (y)."""
    con_derivadas = agregar_variables_derivadas(datos)
    entradas = con_derivadas[VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS]
    objetivo = con_derivadas[COLUMNA_OBJETIVO]
    return entradas, objetivo


def dividir_datos(
    entradas: pd.DataFrame,
    objetivo: pd.Series,
    proporcion_prueba: float = PROPORCION_PRUEBA,
    semilla: int = SEMILLA_REPRODUCIBLE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Divide en entrenamiento y prueba manteniendo la misma proporción de fallas."""
    return train_test_split(
        entradas, objetivo, test_size=proporcion_prueba, stratify=objetivo, random_state=semilla
    )


# --- Modelos ------------------------------------------------------------------------
def crear_preprocesador(escalar: bool) -> ColumnTransformer:
    """Convierte el tipo de producto en columnas 0/1 y, si se pide, escala los números."""
    numericas = StandardScaler() if escalar else "passthrough"
    return ColumnTransformer([
        ("numericas", numericas, VARIABLES_NUMERICAS),
        ("categoricas", OneHotEncoder(handle_unknown="ignore"), VARIABLES_CATEGORICAS),
    ])


def crear_regresion_logistica(semilla: int = SEMILLA_REPRODUCIBLE) -> Pipeline:
    """Modelo base: simple y fácil de explicar. Necesita los números escalados."""
    return Pipeline([
        ("preprocesador", crear_preprocesador(escalar=True)),
        ("modelo", LogisticRegression(
            class_weight="balanced", max_iter=MAX_ITERACIONES_LOGISTICA, random_state=semilla
        )),
    ])


def crear_random_forest(semilla: int = SEMILLA_REPRODUCIBLE) -> Pipeline:
    """Conjunto de árboles de decisión: aprende reglas del tipo 'si potencia > X...'."""
    return Pipeline([
        ("preprocesador", crear_preprocesador(escalar=False)),
        ("modelo", RandomForestClassifier(
            n_estimators=CANTIDAD_ARBOLES, class_weight="balanced", random_state=semilla, n_jobs=-1
        )),
    ])


# --- Evaluación ---------------------------------------------------------------------
def evaluar_modelo(
    modelo: Pipeline,
    entradas: pd.DataFrame,
    objetivo: pd.Series,
    umbral: float = UMBRAL_DECISION,
) -> dict[str, float]:
    """Métricas del modelo sobre datos que no vio al entrenar."""
    probabilidades = modelo.predict_proba(entradas)[:, 1]
    predicciones = (probabilidades >= umbral).astype(int)
    vn, fp, fn, vp = confusion_matrix(objetivo, predicciones, labels=[0, 1]).ravel()
    return {
        "exactitud": round(accuracy_score(objetivo, predicciones), 4),
        "precision": round(precision_score(objetivo, predicciones, zero_division=0), 4),
        "recall": round(recall_score(objetivo, predicciones, zero_division=0), 4),
        "f1": round(f1_score(objetivo, predicciones, zero_division=0), 4),
        "pr_auc": round(average_precision_score(objetivo, probabilidades), 4),
        "verdaderos_negativos": int(vn),
        "falsos_positivos": int(fp),
        "falsos_negativos": int(fn),
        "verdaderos_positivos": int(vp),
    }


def importancia_variables(modelo: Pipeline) -> pd.Series:
    """Cuánto usa el Random Forest cada variable para decidir (suma 1)."""
    nombres = modelo.named_steps["preprocesador"].get_feature_names_out()
    nombres_limpios = [nombre.split("__", 1)[1] for nombre in nombres]
    importancias = modelo.named_steps["modelo"].feature_importances_
    return pd.Series(importancias, index=nombres_limpios).sort_values(ascending=False).round(4)


# --- Riesgo -------------------------------------------------------------------------
def clasificar_riesgo(
    probabilidades: pd.Series | np.ndarray,
    umbral_medio: float = UMBRAL_RIESGO_MEDIO,
    umbral_alto: float = UMBRAL_RIESGO_ALTO,
) -> pd.Series:
    """Convierte la probabilidad de falla en Bajo, Medio o Alto."""
    limites = [-np.inf, umbral_medio, umbral_alto, np.inf]
    niveles = pd.cut(pd.Series(probabilidades), bins=limites, labels=NIVELES_RIESGO, right=False)
    return niveles.astype(str)


def predecir_fuera_de_muestra(
    modelo: Pipeline,
    entradas: pd.DataFrame,
    objetivo: pd.Series,
    semilla: int = SEMILLA_REPRODUCIBLE,
) -> np.ndarray:
    """Probabilidad de falla de cada ciclo usando un modelo que NO vio ese ciclo.

    Divide los datos en 5 partes; para cada parte entrena con las otras 4 y predice.
    Así las predicciones de toda la tabla son honestas (como en datos nuevos).
    """
    pliegues = StratifiedKFold(n_splits=PLIEGUES_VALIDACION, shuffle=True, random_state=semilla)
    return cross_val_predict(modelo, entradas, objetivo, cv=pliegues, method="predict_proba")[:, 1]


def construir_tabla_predicciones(datos: pd.DataFrame, probabilidades: np.ndarray) -> pd.DataFrame:
    """Tabla que leen n8n y Power BI: un ciclo por fila con su probabilidad y riesgo."""
    tabla = datos[["id_registro", "id_maquina", "fecha_hora", "turno", "tipo_producto"]].copy()
    tabla["probabilidad_falla"] = np.round(probabilidades, 4)
    tabla["nivel_riesgo"] = clasificar_riesgo(probabilidades).to_numpy()
    tabla["falla_real"] = datos[COLUMNA_OBJETIVO].to_numpy()
    return tabla
