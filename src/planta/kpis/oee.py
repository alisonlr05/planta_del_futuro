"""Cálculo del OEE (Eficiencia Global de los Equipos).

OEE = Disponibilidad × Rendimiento × Calidad

- Disponibilidad: tiempo que la máquina trabajó / tiempo planificado.
- Rendimiento: velocidad real / velocidad nominal (máximo 100 %).
- Calidad: piezas buenas / piezas totales (un ciclo con falla da una pieza defectuosa).

Los supuestos (minutos de paro, velocidad nominal) están en config.py.
"""

import pandas as pd

from planta.config import (
    HORA_INICIO_JORNADA,
    MINUTOS_CAMBIO_HERRAMIENTA,
    MINUTOS_CICLO,
    MINUTOS_REPARACION_FALLA,
    VELOCIDAD_NOMINAL_RPM,
)

COLUMNAS_TURNO: list[str] = ["id_maquina", "fecha_turno", "turno"]
DECIMALES_INDICADORES: int = 4


# --- Preparación ciclo a ciclo ------------------------------------------------
def asignar_fecha_turno(datos: pd.DataFrame, hora_inicio: int = HORA_INICIO_JORNADA) -> pd.DataFrame:
    """Agrega la fecha de la jornada: de 00:00 a 05:59 cuenta como el día anterior."""
    datos = datos.copy()
    fecha_hora = pd.to_datetime(datos["fecha_hora"])
    datos["fecha_turno"] = (fecha_hora - pd.Timedelta(hours=hora_inicio)).dt.normalize()
    return datos


def marcar_cambios_herramienta(datos: pd.DataFrame) -> pd.DataFrame:
    """Marca con 1 los ciclos donde el desgaste baja dentro de una misma máquina."""
    datos = datos.copy()
    bajada = datos.groupby("id_maquina")["desgaste_herramienta_min"].diff() < 0
    datos["cambio_herramienta"] = bajada.astype(int)
    return datos


def calcular_minutos_paro(
    datos: pd.DataFrame,
    minutos_falla: int = MINUTOS_REPARACION_FALLA,
    minutos_cambio: int = MINUTOS_CAMBIO_HERRAMIENTA,
) -> pd.DataFrame:
    """Minutos de paro de cada ciclo: reparación por falla + cambio de herramienta."""
    datos = datos.copy()
    datos["minutos_paro"] = (
        datos["falla_maquina"] * minutos_falla + datos["cambio_herramienta"] * minutos_cambio
    )
    return datos


def calcular_factor_velocidad(
    datos: pd.DataFrame, velocidad_nominal: int = VELOCIDAD_NOMINAL_RPM
) -> pd.DataFrame:
    """Velocidad real / nominal de cada ciclo, con tope de 1 (no se premia ir más rápido)."""
    datos = datos.copy()
    datos["factor_velocidad"] = (datos["velocidad_rotacion_rpm"] / velocidad_nominal).clip(upper=1)
    return datos


def preparar_ciclos_oee(datos: pd.DataFrame) -> pd.DataFrame:
    """Agrega a cada ciclo todo lo necesario para calcular el OEE."""
    ciclos = asignar_fecha_turno(datos)
    ciclos = marcar_cambios_herramienta(ciclos)
    ciclos = calcular_minutos_paro(ciclos)
    return calcular_factor_velocidad(ciclos)


# --- Agregación -----------------------------------------------------------------
def calcular_oee(ciclos: pd.DataFrame, agrupar_por: list[str]) -> pd.DataFrame:
    """Calcula disponibilidad, rendimiento, calidad y OEE para cada grupo.

    Se calcula desde los ciclos (no promediando OEE ya calculados), así el
    resultado es correcto para cualquier agrupación: turno, día o máquina.
    """
    resumen = ciclos.groupby(agrupar_por, sort=True).agg(
        ciclos=("falla_maquina", "size"),
        fallas=("falla_maquina", "sum"),
        cambios_herramienta=("cambio_herramienta", "sum"),
        tiempo_paro_min=("minutos_paro", "sum"),
        rendimiento=("factor_velocidad", "mean"),
    )
    resumen["tiempo_planificado_min"] = resumen["ciclos"] * MINUTOS_CICLO
    resumen["tiempo_operativo_min"] = resumen["tiempo_planificado_min"] - resumen["tiempo_paro_min"]
    resumen["piezas_defectuosas"] = resumen["fallas"]
    resumen["piezas_buenas"] = resumen["ciclos"] - resumen["piezas_defectuosas"]

    resumen["disponibilidad"] = resumen["tiempo_operativo_min"] / resumen["tiempo_planificado_min"]
    resumen["calidad"] = resumen["piezas_buenas"] / resumen["ciclos"]
    resumen["oee"] = resumen["disponibilidad"] * resumen["rendimiento"] * resumen["calidad"]

    columnas = [
        "ciclos", "tiempo_planificado_min", "tiempo_paro_min", "tiempo_operativo_min",
        "fallas", "cambios_herramienta", "piezas_buenas", "piezas_defectuosas",
        "disponibilidad", "rendimiento", "calidad", "oee",
    ]
    indicadores = ["disponibilidad", "rendimiento", "calidad", "oee"]
    resumen[indicadores] = resumen[indicadores].round(DECIMALES_INDICADORES)
    return resumen[columnas].reset_index()


def calcular_oee_por_turno(datos: pd.DataFrame) -> pd.DataFrame:
    """OEE por máquina, fecha de jornada y turno (la tabla que lee Power BI)."""
    return calcular_oee(preparar_ciclos_oee(datos), COLUMNAS_TURNO)
