"""Pruebas de la simulación de máquinas, fechas y turnos."""

import pandas as pd
import pytest

from planta.features.simulacion import (
    asignar_fechas_horas,
    asignar_maquinas,
    asignar_turnos,
    encontrar_cambios_herramienta,
    inicios_bloques_maquinas,
    obtener_turno,
    simular_operacion_planta,
)

INICIO = "2026-09-01 06:00:00"
CICLO = 30


def crear_tabla_maquinas(ids_maquinas: list[str]) -> pd.DataFrame:
    """Tabla mínima con una columna de máquina, en el orden recibido."""
    return pd.DataFrame({"id_maquina": ids_maquinas})


# --- Turnos -----------------------------------------------------------------
@pytest.mark.parametrize(
    ("hora", "esperado"),
    [
        (6, "Mañana"),   # inicio exacto del turno
        (13, "Mañana"),
        (14, "Tarde"),   # el límite pertenece al turno que empieza
        (21, "Tarde"),
        (22, "Noche"),
        (23, "Noche"),
        (0, "Noche"),    # después de medianoche sigue siendo Noche
        (5, "Noche"),
    ],
)
def test_obtener_turno_devuelve_el_turno_esperado(hora: int, esperado: str) -> None:
    assert obtener_turno(hora) == esperado


def test_cada_hora_del_dia_tiene_un_solo_turno() -> None:
    turnos = [obtener_turno(hora) for hora in range(24)]
    assert turnos.count("Mañana") == 8
    assert turnos.count("Tarde") == 8
    assert turnos.count("Noche") == 8


def test_obtener_turno_da_error_si_la_hora_no_tiene_turno() -> None:
    with pytest.raises(ValueError):
        obtener_turno(3, turnos={"Mañana": (6, 14)})


def test_asignar_turnos_maneja_el_cruce_de_medianoche() -> None:
    datos = pd.DataFrame(
        {"fecha_hora": pd.to_datetime([
            "2026-09-01 21:30", "2026-09-01 22:00", "2026-09-02 00:00",
            "2026-09-02 05:30", "2026-09-02 06:00",
        ])}
    )
    resultado = asignar_turnos(datos)
    assert resultado["turno"].tolist() == ["Tarde", "Noche", "Noche", "Noche", "Mañana"]


# --- Fechas y horas -----------------------------------------------------------
def test_cada_maquina_empieza_en_el_inicio_de_la_simulacion() -> None:
    datos = crear_tabla_maquinas(["M01", "M01", "M02", "M02"])
    resultado = asignar_fechas_horas(datos, inicio=INICIO, minutos_ciclo=CICLO)
    primeras_horas = resultado.groupby("id_maquina")["fecha_hora"].min()
    assert (primeras_horas == pd.Timestamp(INICIO)).all()


def test_registros_de_una_maquina_estan_separados_un_ciclo() -> None:
    datos = crear_tabla_maquinas(["M01"] * 5 + ["M02"] * 3)
    resultado = asignar_fechas_horas(datos, inicio=INICIO, minutos_ciclo=CICLO)
    separaciones = resultado.groupby("id_maquina")["fecha_hora"].diff().dropna()
    assert (separaciones == pd.Timedelta(minutes=CICLO)).all()


def test_las_fechas_pasan_al_dia_siguiente() -> None:
    ciclos_por_dia = 24 * 60 // CICLO  # 48 ciclos de 30 min
    datos = crear_tabla_maquinas(["M01"] * (ciclos_por_dia + 1))
    resultado = asignar_fechas_horas(datos, inicio=INICIO, minutos_ciclo=CICLO)
    assert resultado["fecha_hora"].iloc[-1] == pd.Timestamp("2026-09-02 06:00:00")


# --- Máquinas -----------------------------------------------------------------
def test_encontrar_cambios_herramienta_detecta_bajadas_de_desgaste() -> None:
    desgaste = pd.Series([0, 3, 5, 0, 2, 4, 0, 2])
    assert encontrar_cambios_herramienta(desgaste) == [3, 6]


def test_bloques_de_maquinas_empiezan_en_cambios_de_herramienta() -> None:
    # 3 vidas de herramienta de 4 filas: los cortes caen en 4 y 8.
    desgaste = pd.Series([0, 2, 4, 6] * 3)
    assert inicios_bloques_maquinas(desgaste, cantidad_maquinas=3) == [0, 4, 8]


def test_asignar_maquinas_usa_bloques_contiguos_en_orden() -> None:
    datos = pd.DataFrame({"desgaste_herramienta_min": [0, 2, 4, 6] * 3})
    resultado = asignar_maquinas(datos, ids_maquinas=["M01", "M02", "M03"])
    assert resultado["id_maquina"].tolist() == ["M01"] * 4 + ["M02"] * 4 + ["M03"] * 4


# --- Proceso completo --------------------------------------------------------
def test_simular_operacion_planta_pone_columnas_simuladas_primero() -> None:
    # 5 vidas de herramienta de 4 filas: una por cada máquina (M01..M05).
    datos = pd.DataFrame(
        {"id_registro": range(1, 21), "desgaste_herramienta_min": [0, 2, 4, 6] * 5}
    )
    resultado = simular_operacion_planta(datos)
    assert list(resultado.columns[:4]) == ["id_registro", "id_maquina", "fecha_hora", "turno"]
    assert len(resultado) == len(datos)
    assert resultado["id_maquina"].value_counts().to_dict() == {
        "M01": 4, "M02": 4, "M03": 4, "M04": 4, "M05": 4,
    }
