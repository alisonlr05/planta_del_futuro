"""Pruebas del cálculo de OEE con casos calculados a mano."""

import pandas as pd
import pytest

from planta.kpis.oee import (
    asignar_fecha_turno,
    calcular_factor_velocidad,
    calcular_minutos_paro,
    calcular_oee,
    calcular_oee_por_turno,
    marcar_cambios_herramienta,
)


def crear_ciclos(
    fallas: list[int], cambios: list[int], rpm: list[int], grupo: list[str] | None = None
) -> pd.DataFrame:
    """Ciclos ya preparados (con paro y factor de velocidad) para probar calcular_oee."""
    ciclos = pd.DataFrame({
        "grupo": grupo or ["A"] * len(fallas),
        "falla_maquina": fallas,
        "cambio_herramienta": cambios,
        "velocidad_rotacion_rpm": rpm,
    })
    return calcular_factor_velocidad(calcular_minutos_paro(ciclos))


# --- Fecha de la jornada ----------------------------------------------------
@pytest.mark.parametrize(
    ("fecha_hora", "fecha_esperada"),
    [
        ("2026-09-01T06:00:00", "2026-09-01"),  # inicio de la jornada
        ("2026-09-01T22:00:00", "2026-09-01"),  # inicio del turno Noche
        ("2026-09-02T00:00:00", "2026-09-01"),  # medianoche: sigue siendo la jornada anterior
        ("2026-09-02T05:30:00", "2026-09-01"),  # último ciclo del turno Noche
        ("2026-09-02T06:00:00", "2026-09-02"),  # empieza una jornada nueva
    ],
)
def test_asignar_fecha_turno(fecha_hora: str, fecha_esperada: str) -> None:
    resultado = asignar_fecha_turno(pd.DataFrame({"fecha_hora": [fecha_hora]}))
    assert resultado["fecha_turno"].iloc[0] == pd.Timestamp(fecha_esperada)


# --- Preparación ciclo a ciclo ------------------------------------------------
def test_cambios_de_herramienta_se_cuentan_dentro_de_cada_maquina() -> None:
    datos = pd.DataFrame({
        "id_maquina": ["M01", "M01", "M01", "M02", "M02", "M02"],
        "desgaste_herramienta_min": [0, 5, 10, 0, 4, 0],
    })
    resultado = marcar_cambios_herramienta(datos)
    # El paso de M01 (10) a M02 (0) NO es un cambio; la bajada 4 -> 0 en M02 sí.
    assert resultado["cambio_herramienta"].tolist() == [0, 0, 0, 0, 0, 1]


def test_minutos_paro_suman_reparacion_y_cambio_de_herramienta() -> None:
    datos = pd.DataFrame({"falla_maquina": [0, 1, 0, 1], "cambio_herramienta": [0, 0, 1, 1]})
    resultado = calcular_minutos_paro(datos, minutos_falla=20, minutos_cambio=5)
    assert resultado["minutos_paro"].tolist() == [0, 20, 5, 25]


def test_factor_velocidad_tiene_tope_de_uno() -> None:
    datos = pd.DataFrame({"velocidad_rotacion_rpm": [1500, 1200, 3000]})
    resultado = calcular_factor_velocidad(datos, velocidad_nominal=1500)
    assert resultado["factor_velocidad"].tolist() == [1.0, 0.8, 1.0]


# --- Cálculo del OEE ------------------------------------------------------------
def test_calcular_oee_caso_calculado_a_mano() -> None:
    # 4 ciclos de 30 min = 120 min planificados.
    # Paro: 1 falla (20) + 1 cambio (5) = 25 min -> disponibilidad = 95/120.
    # Rendimiento: promedio(1, 1, 0.8, 1) = 0.95.
    # Calidad: 3 piezas buenas de 4 = 0.75.
    ciclos = crear_ciclos(fallas=[1, 0, 0, 0], cambios=[0, 1, 0, 0], rpm=[1500, 1500, 1200, 1500])
    fila = calcular_oee(ciclos, ["grupo"]).iloc[0]

    assert fila["tiempo_planificado_min"] == 120
    assert fila["tiempo_paro_min"] == 25
    assert fila["tiempo_operativo_min"] == 95
    assert fila["piezas_buenas"] == 3
    assert fila["disponibilidad"] == pytest.approx(95 / 120, abs=1e-4)
    assert fila["rendimiento"] == pytest.approx(0.95, abs=1e-4)
    assert fila["calidad"] == pytest.approx(0.75, abs=1e-4)
    assert fila["oee"] == pytest.approx(95 / 120 * 0.95 * 0.75, abs=1e-4)


def test_oee_es_100_por_ciento_sin_paros_ni_fallas_a_velocidad_nominal() -> None:
    ciclos = crear_ciclos(fallas=[0, 0], cambios=[0, 0], rpm=[1500, 1600])
    fila = calcular_oee(ciclos, ["grupo"]).iloc[0]
    assert fila["oee"] == 1.0


def test_oee_total_se_calcula_desde_ciclos_y_no_promediando_grupos() -> None:
    # Grupo A: 1 ciclo con falla (calidad 0). Grupo B: 3 ciclos buenos (calidad 1).
    # Promediar daría 0.5; lo correcto es 3 buenas de 4 = 0.75.
    ciclos = crear_ciclos(
        fallas=[1, 0, 0, 0], cambios=[0, 0, 0, 0], rpm=[1500] * 4, grupo=["A", "B", "B", "B"]
    )
    total = calcular_oee(ciclos.assign(grupo="Total"), ["grupo"]).iloc[0]
    assert total["calidad"] == pytest.approx(0.75)


def test_oee_por_turno_agrupa_el_turno_noche_que_cruza_medianoche() -> None:
    datos = pd.DataFrame({
        "id_maquina": ["M01", "M01", "M01"],
        "fecha_hora": ["2026-09-01T22:00:00", "2026-09-02T01:00:00", "2026-09-02T06:00:00"],
        "turno": ["Noche", "Noche", "Mañana"],
        "desgaste_herramienta_min": [10, 12, 14],
        "falla_maquina": [0, 0, 0],
        "velocidad_rotacion_rpm": [1500, 1500, 1500],
    })
    resultado = calcular_oee_por_turno(datos).set_index("turno")

    assert len(resultado) == 2  # un turno Noche (2 ciclos) y un turno Mañana (1 ciclo)
    assert resultado.loc["Noche", "ciclos"] == 2
    assert resultado.loc["Noche", "fecha_turno"] == pd.Timestamp("2026-09-01")
    assert resultado.loc["Mañana", "fecha_turno"] == pd.Timestamp("2026-09-02")
