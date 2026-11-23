"""Pruebas de las alertas: señales, mensajes y agrupación por turno."""

import pandas as pd
import pytest

from planta.features.variables import agregar_variables_derivadas
from planta.models.alertas import (
    SIN_SENAL_CLARA,
    agrupar_alertas_por_turno,
    construir_asunto,
    construir_cuerpo_html,
    describir_causa_probable,
    detectar_senales,
    formatear_miles,
    preparar_alertas,
)

# Un ciclo "normal": diferencia 11 °C, potencia ≈ 6 283 W, esfuerzo 2 000 Nm·min.
CICLO_NORMAL = {
    "tipo_producto": "L",
    "temperatura_aire_c": 25.0,
    "temperatura_proceso_c": 36.0,
    "velocidad_rotacion_rpm": 1500,
    "torque_nm": 40.0,
    "desgaste_herramienta_min": 50,
}


def crear_ciclo(**cambios: float | str) -> pd.Series:
    """Ciclo normal con los cambios indicados y sus variables derivadas."""
    datos = pd.DataFrame([{**CICLO_NORMAL, **cambios}])
    return agregar_variables_derivadas(datos).iloc[0]


def acciones(ciclo: pd.Series) -> list[str]:
    return [accion for _, accion in detectar_senales(ciclo)]


# --- Señales ------------------------------------------------------------------------
def test_ciclo_normal_no_tiene_senales() -> None:
    assert detectar_senales(crear_ciclo()) == []


def test_detecta_calor_con_poca_diferencia_y_baja_velocidad() -> None:
    ciclo = crear_ciclo(temperatura_proceso_c=33.0, velocidad_rotacion_rpm=1300)  # dif 8 °C
    assert "Revisar refrigeración/ventilación" in acciones(ciclo)


def test_poca_diferencia_con_velocidad_alta_no_es_calor() -> None:
    ciclo = crear_ciclo(temperatura_proceso_c=33.0, velocidad_rotacion_rpm=1500)
    assert "Revisar refrigeración/ventilación" not in acciones(ciclo)


@pytest.mark.parametrize(
    ("rpm", "torque", "texto"),
    [(1500, 20.0, "Potencia baja"), (2500, 40.0, "Potencia alta")],  # ≈ 3 142 W y ≈ 10 472 W
)
def test_detecta_potencia_fuera_de_rango(rpm: int, torque: float, texto: str) -> None:
    senales = detectar_senales(crear_ciclo(velocidad_rotacion_rpm=rpm, torque_nm=torque))
    assert any(senal.startswith(texto) for senal, _ in senales)


def test_limite_de_sobreesfuerzo_depende_del_tipo_de_producto() -> None:
    # 190 min × 60 Nm = 11 400 Nm·min: supera el límite de L (11 000) pero no el de H (13 000).
    cambios = {"desgaste_herramienta_min": 190, "torque_nm": 60.0, "velocidad_rotacion_rpm": 1400}
    assert "Reducir carga o cambiar herramienta" in acciones(crear_ciclo(tipo_producto="L", **cambios))
    assert "Reducir carga o cambiar herramienta" not in acciones(crear_ciclo(tipo_producto="H", **cambios))


def test_detecta_herramienta_desgastada_desde_200_minutos() -> None:
    assert "Cambiar herramienta" not in acciones(crear_ciclo(desgaste_herramienta_min=199))
    assert "Cambiar herramienta" in acciones(crear_ciclo(desgaste_herramienta_min=200))


def test_sin_senales_se_sugiere_inspeccion_general() -> None:
    assert describir_causa_probable(crear_ciclo()) == SIN_SENAL_CLARA


def test_varias_senales_se_unen_en_un_solo_texto() -> None:
    ciclo = crear_ciclo(velocidad_rotacion_rpm=2500, desgaste_herramienta_min=210)
    senal, accion = describir_causa_probable(ciclo)
    assert senal.startswith("Potencia alta") and "Herramienta desgastada (210 min)" in senal
    assert accion == "Revisar parámetros de corte; Cambiar herramienta"


# --- Mensajes -----------------------------------------------------------------------
def test_formatear_miles_usa_espacio() -> None:
    assert formatear_miles(9450.4) == "9 450"


@pytest.mark.parametrize(("cantidad", "palabra"), [(1, "1 alerta "), (3, "3 alertas ")])
def test_asunto_usa_singular_y_plural(cantidad: int, palabra: str) -> None:
    asunto = construir_asunto(pd.Timestamp("2026-09-02"), "Mañana", cantidad)
    assert palabra in asunto
    assert asunto.endswith("Turno Mañana · 2026-09-02")


def test_cuerpo_html_tiene_una_fila_por_alerta_y_escapa_texto() -> None:
    alertas = pd.DataFrame({
        "id_maquina": ["M01", "M03"],
        "fecha_hora": pd.to_datetime(["2026-09-02 07:00", "2026-09-02 09:30"]),
        "probabilidad_falla": [0.97, 0.8],
        "senal": ["Potencia <alta>", "Calor"],
        "accion_sugerida": ["Revisar", "Revisar"],
    })
    html = construir_cuerpo_html(alertas)
    assert html.count("<tr>") == 3  # encabezado + 2 alertas
    assert "97%" in html and "2026-09-02 07:00" in html
    assert "&lt;alta&gt;" in html  # el texto no rompe el HTML
    assert "\n" not in html  # una sola línea: no rompe el CSV


# --- Tabla de alertas y agrupación ----------------------------------------------------
def crear_entradas() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Producción y predicciones mínimas: 3 ciclos en riesgo Alto y 1 en Bajo."""
    fechas = ["2026-09-01T23:00:00", "2026-09-01T07:00:00", "2026-09-02T03:30:00", "2026-09-01T16:00:00"]
    predicciones = pd.DataFrame({
        "id_registro": [1, 2, 3, 4],
        "id_maquina": ["M01", "M02", "M03", "M04"],
        "fecha_hora": fechas,
        "turno": ["Noche", "Mañana", "Noche", "Tarde"],
        "tipo_producto": ["L"] * 4,
        "probabilidad_falla": [0.9, 0.8, 0.7, 0.1],
        "nivel_riesgo": ["Alto", "Alto", "Alto", "Bajo"],
        "falla_real": [1, 1, 0, 0],
    })
    produccion = pd.DataFrame([{**CICLO_NORMAL, "id_registro": i} for i in [1, 2, 3, 4]])
    return produccion, predicciones


def test_preparar_alertas_solo_incluye_riesgo_alto_y_asigna_jornada() -> None:
    alertas = preparar_alertas(*crear_entradas())
    assert alertas["id_registro"].tolist() == [2, 1, 3]  # ordenadas por fecha y hora
    ciclo_madrugada = alertas.set_index("id_registro").loc[3]
    assert ciclo_madrugada["fecha_turno"] == pd.Timestamp("2026-09-01")  # 03:30 -> jornada anterior


def test_agrupar_da_un_correo_por_turno_en_orden_cronologico() -> None:
    por_turno = agrupar_alertas_por_turno(preparar_alertas(*crear_entradas()))
    assert por_turno["id_envio"].tolist() == ["2026-09-01_Mañana", "2026-09-01_Noche"]
    assert por_turno["cantidad_alertas"].tolist() == [1, 2]
    assert por_turno.loc[1, "maquinas"] == "M01, M03"
    assert por_turno["id_envio"].is_unique
