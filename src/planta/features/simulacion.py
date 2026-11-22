"""Simulación de la operación de la planta: máquinas, fecha y hora, y turnos.

El dataset AI4I 2020 no trae máquinas ni fechas. Aquí se agregan de forma
reproducible (sin azar), respetando el orden original de las filas.
"""

import pandas as pd

from planta.config import IDS_MAQUINAS, INICIO_SIMULACION, MINUTOS_CICLO, TURNOS

COLUMNA_DESGASTE: str = "desgaste_herramienta_min"
COLUMNA_MAQUINA: str = "id_maquina"
COLUMNA_FECHA_HORA: str = "fecha_hora"
COLUMNA_TURNO: str = "turno"


# --- 1. Revisión del desgaste de herramienta --------------------------------
def encontrar_cambios_herramienta(desgaste: pd.Series) -> list[int]:
    """Posiciones donde el desgaste baja: ahí se cambió la herramienta."""
    bajadas = desgaste.diff() < 0
    return [int(posicion) for posicion in bajadas.to_numpy().nonzero()[0]]


def describir_secuencia_desgaste(desgaste: pd.Series) -> dict[str, float]:
    """Resume cómo evoluciona el desgaste fila a fila en el orden original."""
    pasos = desgaste.diff().dropna()
    cambios = encontrar_cambios_herramienta(desgaste)
    numero_de_vida = (desgaste.diff() < 0).cumsum().to_numpy()
    filas_por_vida = pd.Series(range(len(desgaste))).groupby(numero_de_vida).size()
    return {
        "pasos_que_suben": int((pasos > 0).sum()),
        "pasos_iguales": int((pasos == 0).sum()),
        "pasos_que_bajan": int((pasos < 0).sum()),
        "aumento_promedio_min": round(float(pasos[pasos > 0].mean()), 2),
        "cambios_de_herramienta": len(cambios),
        "vidas_de_herramienta": len(filas_por_vida),
        "filas_promedio_por_vida": round(float(filas_por_vida.mean()), 1),
    }


# --- 2. Asignación de máquinas ----------------------------------------------
def inicios_bloques_maquinas(desgaste: pd.Series, cantidad_maquinas: int) -> list[int]:
    """Inicio de cada bloque: el cambio de herramienta más cercano a un corte parejo.

    Así cada máquina arranca con herramienta nueva y no se parte una vida a la mitad.
    """
    cambios = encontrar_cambios_herramienta(desgaste)
    tamano_bloque = len(desgaste) / cantidad_maquinas
    inicios = [0]
    for k in range(1, cantidad_maquinas):
        corte_ideal = k * tamano_bloque
        inicios.append(min(cambios, key=lambda posicion: abs(posicion - corte_ideal)))
    return inicios


def asignar_maquinas(datos: pd.DataFrame, ids_maquinas: list[str] = IDS_MAQUINAS) -> pd.DataFrame:
    """Asigna cada fila a una máquina en bloques contiguos (M01, M02, ...)."""
    limites = inicios_bloques_maquinas(datos[COLUMNA_DESGASTE], len(ids_maquinas)) + [len(datos)]
    etiquetas: list[str] = []
    for id_maquina, inicio, fin in zip(ids_maquinas, limites[:-1], limites[1:]):
        etiquetas.extend([id_maquina] * (fin - inicio))
    datos = datos.copy()
    datos[COLUMNA_MAQUINA] = etiquetas
    return datos


# --- 3. Fecha y hora -----------------------------------------------------------
def asignar_fechas_horas(
    datos: pd.DataFrame,
    inicio: str = INICIO_SIMULACION,
    minutos_ciclo: int = MINUTOS_CICLO,
) -> pd.DataFrame:
    """Da a cada fila su fecha y hora: un ciclo cada `minutos_ciclo` por máquina."""
    numero_ciclo = datos.groupby(COLUMNA_MAQUINA, sort=False).cumcount()
    datos = datos.copy()
    datos[COLUMNA_FECHA_HORA] = pd.Timestamp(inicio) + pd.to_timedelta(
        numero_ciclo * minutos_ciclo, unit="min"
    )
    return datos


# --- 4. Turnos -----------------------------------------------------------------
def obtener_turno(hora: int, turnos: dict[str, tuple[int, int]] = TURNOS) -> str:
    """Devuelve el turno de una hora del día (0-23). Soporta turnos que cruzan la medianoche."""
    for nombre, (hora_inicio, hora_fin) in turnos.items():
        if hora_inicio < hora_fin and hora_inicio <= hora < hora_fin:
            return nombre
        if hora_inicio > hora_fin and (hora >= hora_inicio or hora < hora_fin):  # ej. Noche 22 -> 06
            return nombre
    raise ValueError(f"La hora {hora} no pertenece a ningún turno.")


def asignar_turnos(datos: pd.DataFrame) -> pd.DataFrame:
    """Agrega la columna de turno según la hora de cada registro."""
    datos = datos.copy()
    datos[COLUMNA_TURNO] = datos[COLUMNA_FECHA_HORA].dt.hour.map(obtener_turno)
    return datos


# --- Proceso completo --------------------------------------------------------
def simular_operacion_planta(datos: pd.DataFrame) -> pd.DataFrame:
    """Agrega máquina, fecha y hora, y turno; deja esas columnas al inicio."""
    simulados = asignar_turnos(asignar_fechas_horas(asignar_maquinas(datos)))
    primeras_columnas = ["id_registro", COLUMNA_MAQUINA, COLUMNA_FECHA_HORA, COLUMNA_TURNO]
    otras_columnas = [col for col in simulados.columns if col not in primeras_columnas]
    return simulados[primeras_columnas + otras_columnas]
