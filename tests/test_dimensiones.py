"""Pruebas de las tablas de dimensiones para Power BI."""

import pandas as pd

from planta.config import IDS_MAQUINAS, TURNOS
from planta.data.dimensiones import (
    crear_dim_fechas,
    crear_dim_fechas_desde_datos,
    crear_dim_maquinas,
    crear_dim_turnos,
)


# --- Máquinas -------------------------------------------------------------------
def test_dim_maquinas_tiene_una_fila_por_maquina():
    maquinas = crear_dim_maquinas()
    assert maquinas["id_maquina"].tolist() == IDS_MAQUINAS
    assert maquinas["id_maquina"].is_unique


def test_dim_maquinas_arma_el_nombre_para_mostrar():
    maquinas = crear_dim_maquinas(["M01", "M12"])
    assert maquinas["nombre_maquina"].tolist() == ["Máquina 01", "Máquina 12"]


# --- Turnos ---------------------------------------------------------------------
def test_dim_turnos_respeta_el_orden_de_la_jornada():
    turnos = crear_dim_turnos()
    assert turnos["turno"].tolist() == list(TURNOS)
    assert turnos["orden_turno"].tolist() == [1, 2, 3]


def test_dim_turnos_muestra_el_horario():
    turnos = crear_dim_turnos({"Noche": (22, 6)})
    assert turnos.loc[0, "horario"] == "22:00-06:00"


# --- Calendario -----------------------------------------------------------------
def test_dim_fechas_incluye_ambos_extremos_sin_saltar_dias():
    fechas = crear_dim_fechas(pd.Timestamp("2026-09-28"), pd.Timestamp("2026-10-03"))
    assert len(fechas) == 6
    assert fechas["fecha"].diff().dropna().eq(pd.Timedelta(days=1)).all()


def test_dim_fechas_nombres_en_espanol():
    fechas = crear_dim_fechas(pd.Timestamp("2026-09-05"), pd.Timestamp("2026-09-05"))  # sábado
    fila = fechas.iloc[0]
    assert fila["mes_nombre"] == "Septiembre"
    assert fila["dia_semana_nombre"] == "Sábado"
    assert fila["dia_semana_numero"] == 6
    assert fila["es_fin_de_semana"] == 1


def test_dim_fechas_lunes_no_es_fin_de_semana():
    fechas = crear_dim_fechas(pd.Timestamp("2026-09-07"), pd.Timestamp("2026-09-07"))  # lunes
    assert fechas.loc[0, "dia_semana_numero"] == 1
    assert fechas.loc[0, "es_fin_de_semana"] == 0


def test_dim_fechas_ignora_la_hora():
    fechas = crear_dim_fechas(pd.Timestamp("2026-09-01 22:30"), pd.Timestamp("2026-09-02 05:30"))
    assert fechas["fecha"].tolist() == [pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-02")]


def test_dim_fechas_desde_datos_cubre_todas_las_fechas():
    datos = pd.Series(["2026-09-03T00:00:00", "2026-09-01T00:00:00", "2026-09-05T00:00:00"])
    fechas = crear_dim_fechas_desde_datos(datos)
    assert fechas["fecha"].min() == pd.Timestamp("2026-09-01")
    assert fechas["fecha"].max() == pd.Timestamp("2026-09-05")
    assert set(pd.to_datetime(datos)) <= set(fechas["fecha"])
