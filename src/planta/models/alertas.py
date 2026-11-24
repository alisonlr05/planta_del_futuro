"""Alertas de riesgo de falla: causa probable, acción sugerida y correo por turno.

El modelo dice QUÉ ciclo tiene riesgo alto; este módulo explica POR QUÉ
(señal física) y QUÉ HACER (acción sugerida), y arma un correo por turno
que n8n solo tiene que enviar.
"""

from html import escape

import pandas as pd

from planta.config import (
    DESGASTE_CAMBIO_HERRAMIENTA_MIN,
    DIFERENCIA_TEMPERATURA_MINIMA_C,
    LIMITE_ESFUERZO_NM_MIN,
    NIVEL_RIESGO_ALERTA,
    POTENCIA_MAXIMA_W,
    POTENCIA_MINIMA_W,
    VELOCIDAD_MINIMA_DISIPACION_RPM,
)
from planta.features.variables import agregar_variables_derivadas
from planta.kpis.oee import asignar_fecha_turno

ORDEN_TURNOS: dict[str, int] = {"Mañana": 1, "Tarde": 2, "Noche": 3}
SIN_SENAL_CLARA: tuple[str, str] = (
    "Combinación de variables fuera de lo normal",
    "Inspección general de la máquina",
)
COLUMNAS_MEDICIONES: list[str] = [
    "id_registro", "temperatura_aire_c", "temperatura_proceso_c",
    "velocidad_rotacion_rpm", "torque_nm", "desgaste_herramienta_min",
]


# --- Causa probable de cada alerta --------------------------------------------
def formatear_miles(valor: float) -> str:
    """Número entero con espacio como separador de miles (ej. 9 450)."""
    return f"{valor:,.0f}".replace(",", " ")


def detectar_senales(ciclo: pd.Series) -> list[tuple[str, str]]:
    """Señales físicas fuera de rango en un ciclo: lista de (señal, acción sugerida)."""
    senales: list[tuple[str, str]] = []
    diferencia = ciclo["diferencia_temperatura_c"]
    if diferencia < DIFERENCIA_TEMPERATURA_MINIMA_C and ciclo["velocidad_rotacion_rpm"] < VELOCIDAD_MINIMA_DISIPACION_RPM:
        senales.append((f"Diferencia de temperatura baja ({diferencia:.1f} °C)", "Revisar refrigeración/ventilación"))

    potencia = ciclo["potencia_w"]
    if potencia < POTENCIA_MINIMA_W:
        senales.append((f"Potencia baja ({formatear_miles(potencia)} W)", "Revisar parámetros de corte"))
    elif potencia > POTENCIA_MAXIMA_W:
        senales.append((f"Potencia alta ({formatear_miles(potencia)} W)", "Revisar parámetros de corte"))

    esfuerzo = ciclo["esfuerzo_nm_min"]
    if esfuerzo > LIMITE_ESFUERZO_NM_MIN[ciclo["tipo_producto"]]:
        senales.append((f"Sobreesfuerzo ({formatear_miles(esfuerzo)} Nm·min)", "Reducir carga o cambiar herramienta"))

    desgaste = ciclo["desgaste_herramienta_min"]
    if desgaste >= DESGASTE_CAMBIO_HERRAMIENTA_MIN:
        senales.append((f"Herramienta desgastada ({desgaste:.0f} min)", "Cambiar herramienta"))
    return senales


def describir_causa_probable(ciclo: pd.Series) -> tuple[str, str]:
    """Une las señales de un ciclo en un texto de señal y uno de acción."""
    senales = detectar_senales(ciclo) or [SIN_SENAL_CLARA]
    textos_senal = "; ".join(senal for senal, _ in senales)
    acciones = "; ".join(dict.fromkeys(accion for _, accion in senales))  # sin repetir
    return textos_senal, acciones


# --- Tabla de alertas (un ciclo por fila) -------------------------------------
COLUMNAS_ALERTA: list[str] = [
    "id_registro", "id_maquina", "fecha_hora", "fecha_turno", "turno", "probabilidad_falla",
]


def preparar_ciclos_en_riesgo(produccion: pd.DataFrame, predicciones: pd.DataFrame) -> pd.DataFrame:
    """Ciclos en riesgo Alto con sus mediciones, variables derivadas y jornada."""
    en_riesgo = predicciones[predicciones["nivel_riesgo"] == NIVEL_RIESGO_ALERTA]
    ciclos = en_riesgo.merge(produccion[COLUMNAS_MEDICIONES], on="id_registro", how="left")
    ciclos = asignar_fecha_turno(agregar_variables_derivadas(ciclos))
    ciclos["fecha_hora"] = pd.to_datetime(ciclos["fecha_hora"])
    return ciclos.sort_values("fecha_hora").reset_index(drop=True)


def preparar_alertas(produccion: pd.DataFrame, predicciones: pd.DataFrame) -> pd.DataFrame:
    """Ciclos en riesgo Alto con su jornada, señal y acción sugerida."""
    alertas = preparar_ciclos_en_riesgo(produccion, predicciones)
    causas = alertas.apply(describir_causa_probable, axis=1, result_type="expand")
    alertas["senal"], alertas["accion_sugerida"] = causas[0], causas[1]
    return alertas[COLUMNAS_ALERTA + ["senal", "accion_sugerida"]]


# --- Detalle para Power BI (una señal por fila) ---------------------------------
def extraer_tipo_senal(senal: str) -> str:
    """Quita el valor medido para poder agrupar: 'Potencia baja (3 410 W)' -> 'Potencia baja'."""
    return senal.split(" (")[0]


def desglosar_senales(ciclos_en_riesgo: pd.DataFrame) -> pd.DataFrame:
    """Una fila por cada señal de cada alerta, con su acción sugerida.

    Una alerta con dos señales ocupa dos filas; por eso en Power BI las alertas
    (en total o por acción) se cuentan con DISTINCTCOUNT(id_registro).
    """
    filas = []
    for _, ciclo in ciclos_en_riesgo.iterrows():
        for senal, accion in detectar_senales(ciclo) or [SIN_SENAL_CLARA]:
            filas.append({
                **ciclo[COLUMNAS_ALERTA].to_dict(),
                "tipo_senal": extraer_tipo_senal(senal),
                "senal": senal,
                "accion_sugerida": accion,
            })
    return pd.DataFrame(filas)


# --- Correo por turno -----------------------------------------------------------
def construir_asunto(fecha_turno: pd.Timestamp, turno: str, cantidad: int) -> str:
    """Asunto del correo, ej. '⚠️ 3 alertas de riesgo ALTO · Turno Mañana · 2026-09-02'."""
    palabra = "alerta" if cantidad == 1 else "alertas"
    return f"⚠️ {cantidad} {palabra} de riesgo ALTO · Turno {turno} · {fecha_turno:%Y-%m-%d}"


def construir_cuerpo_html(alertas_turno: pd.DataFrame) -> str:
    """Tabla HTML con las alertas de un turno (estilos en línea para clientes de correo)."""
    celda = 'style="padding:6px 10px;border-bottom:1px solid #e4e3df;text-align:left"'
    encabezados = ["Máquina", "Fecha y hora", "Probabilidad", "Señal", "Acción sugerida"]
    filas_html = "".join(
        "<tr>"
        f"<td {celda}><b>{escape(alerta.id_maquina)}</b></td>"
        f"<td {celda}>{alerta.fecha_hora:%Y-%m-%d %H:%M}</td>"
        f"<td {celda}>{alerta.probabilidad_falla:.0%}</td>"
        f"<td {celda}>{escape(alerta.senal)}</td>"
        f"<td {celda}>{escape(alerta.accion_sugerida)}</td>"
        "</tr>"
        for alerta in alertas_turno.itertuples()
    )
    encabezado_html = "".join(f"<th {celda}>{texto}</th>" for texto in encabezados)
    return (
        '<div style="font-family:Arial,sans-serif;font-size:14px;color:#0b0b0b">'
        "<p>El modelo de predicción detectó ciclos con <b>riesgo ALTO de falla</b> en este turno:</p>"
        f'<table style="border-collapse:collapse"><thead style="background:#f0efec"><tr>{encabezado_html}</tr></thead>'
        f"<tbody>{filas_html}</tbody></table>"
        '<p style="color:#52514e;font-size:12px">Planta del Futuro · alerta automática generada con n8n.</p>'
        "</div>"
    )


def agrupar_alertas_por_turno(alertas: pd.DataFrame) -> pd.DataFrame:
    """Una fila por turno con alertas: lo que n8n envía como un correo."""
    filas = []
    for (fecha_turno, turno), grupo in alertas.groupby(["fecha_turno", "turno"], sort=False):
        filas.append({
            "id_envio": f"{fecha_turno:%Y-%m-%d}_{turno}",
            "fecha_turno": fecha_turno,
            "turno": turno,
            "orden_turno": ORDEN_TURNOS[turno],
            "cantidad_alertas": len(grupo),
            "maquinas": ", ".join(sorted(grupo["id_maquina"].unique())),
            "asunto": construir_asunto(fecha_turno, turno, len(grupo)),
            "cuerpo_html": construir_cuerpo_html(grupo),
        })
    por_turno = pd.DataFrame(filas).sort_values(["fecha_turno", "orden_turno"])
    return por_turno.drop(columns="orden_turno").reset_index(drop=True)
