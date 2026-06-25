"""
NEXORA · Módulo de Inteligencia Predictiva
==========================================
persistencia.py — Capa centralizada de persistencia de métricas y predicciones.

Doble destino (dual sink), siempre en este orden de robustez:

    1. Archivos en ``nexora-ml/reports`` (JSON/CSV) — fuente de verdad local,
       siempre disponible, no requiere base de datos. Es lo que consumen el
       dashboard BI y los endpoints GET /metrics y GET /predictions.
    2. Tablas en Neon (PostgreSQL) — opcional. Solo se usa si hay una URL de
       conexión en el entorno (DATABASE_URL / DB_URL / NEON_DATABASE_URL).

El módulo es *best-effort* respecto a la base de datos: si no hay URL, o si la
conexión falla, se registra una advertencia y se continúa con los archivos.
Así el servicio es desplegable en Render con o sin Neon configurado.

Sin credenciales embebidas: la conexión se resuelve siempre desde el entorno.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DIR_REPORTS = RAIZ / "reports"
DIR_DATA = RAIZ / "data"
DIR_LOGS = RAIZ / "logs"
for _d in (DIR_REPORTS, DIR_DATA, DIR_LOGS):
    _d.mkdir(parents=True, exist_ok=True)

RUTA_METRICAS = DIR_REPORTS / "metricas.json"
RUTA_PREDICCIONES_JSON = DIR_REPORTS / "predicciones.json"
RUTA_PREDICCIONES_CSV = DIR_REPORTS / "predicciones.csv"
# Salida histórica del pipeline; se usa como respaldo de lectura.
RUTA_SCOREADOS = DIR_DATA / "clientes_scoreados.csv"

logger = logging.getLogger("nexora.persistencia")


# --- Resolución de la base de datos (delegada al punto único del proyecto) ---
def resolver_database_url() -> str | None:
    """
    Resuelve la URL de PostgreSQL desde el entorno.

    Reutiliza ``carga.neon_connection`` cuando el paquete raíz está disponible
    (ejecución vía API o pipeline); en ejecución aislada del módulo IA cae a una
    resolución local equivalente. Ambas leen las mismas variables de entorno.
    """
    try:
        from carga.neon_connection import resolver_database_url as _resolver
        return _resolver()
    except Exception:  # noqa: BLE001 — fallback intencional para ejecución aislada
        import os

        for var in ("DATABASE_URL", "DB_URL", "NEON_DATABASE_URL"):
            valor = os.getenv(var)
            if valor:
                return valor
        return None


def _conectar():
    """Devuelve una conexión psycopg2 o None si no hay BD configurada/disponible."""
    url = resolver_database_url()
    if not url:
        return None
    try:
        import psycopg2

        conn = psycopg2.connect(url)
        conn.autocommit = False
        return conn
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo conectar a la base de datos: %s", exc)
        return None


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Persistencia de MÉTRICAS ------------------------------------------------
def guardar_metricas(metricas: dict) -> dict:
    """
    Persiste el resumen de métricas del entrenamiento.

    Siempre escribe ``reports/metricas.json``. Si hay BD configurada, además
    inserta una fila en la tabla ``ml_metricas`` (con el JSON completo en una
    columna ``payload`` y las métricas clave del modelo seleccionado).

    Devuelve un dict con el detalle de los destinos efectivamente usados.
    """
    destinos = {"archivo": str(RUTA_METRICAS), "base_datos": False}

    RUTA_METRICAS.write_text(
        json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    conn = _conectar()
    if conn is None:
        return destinos
    try:
        seleccionado = metricas.get("modelo_seleccionado", "")
        met = metricas.get("metricas_por_modelo", {}).get(seleccionado, {})
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ml_metricas (
                    id SERIAL PRIMARY KEY,
                    ts TIMESTAMPTZ DEFAULT NOW(),
                    modelo_seleccionado TEXT,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1 REAL,
                    roc_auc REAL,
                    gini REAL,
                    tiempo_total_s REAL,
                    payload JSONB
                );
                """
            )
            cur.execute(
                """
                INSERT INTO ml_metricas
                    (modelo_seleccionado, accuracy, precision, recall, f1,
                     roc_auc, gini, tiempo_total_s, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    seleccionado,
                    met.get("accuracy"),
                    met.get("precision"),
                    met.get("recall"),
                    met.get("f1"),
                    met.get("roc_auc"),
                    met.get("gini"),
                    metricas.get("tiempo_total_s"),
                    json.dumps(metricas, ensure_ascii=False),
                ),
            )
        conn.commit()
        destinos["base_datos"] = True
        logger.info("Métricas insertadas en Neon (tabla ml_metricas).")
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        logger.warning("No se pudieron guardar métricas en BD: %s", exc)
    finally:
        conn.close()
    return destinos


def leer_metricas() -> dict:
    """Lee las últimas métricas desde ``reports/metricas.json`` (o dict vacío)."""
    if RUTA_METRICAS.exists():
        return json.loads(RUTA_METRICAS.read_text(encoding="utf-8"))
    return {}


# --- Persistencia de PREDICCIONES --------------------------------------------
def guardar_predicciones(df: pd.DataFrame) -> dict:
    """
    Persiste el DataFrame scoreado en ``reports/`` (JSON + CSV) y, si hay BD,
    en la tabla ``ml_predicciones`` (cada fila como JSON + columnas clave para
    consulta directa).
    """
    destinos = {
        "archivo_json": str(RUTA_PREDICCIONES_JSON),
        "archivo_csv": str(RUTA_PREDICCIONES_CSV),
        "base_datos": False,
        "filas": int(len(df)),
    }

    registros = df.to_dict(orient="records")
    RUTA_PREDICCIONES_JSON.write_text(
        json.dumps(
            {"generado_en": _ahora_iso(), "total": len(registros), "predicciones": registros},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    df.to_csv(RUTA_PREDICCIONES_CSV, index=False, encoding="utf-8")

    conn = _conectar()
    if conn is None:
        return destinos
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ml_predicciones (
                    id SERIAL PRIMARY KEY,
                    ts TIMESTAMPTZ DEFAULT NOW(),
                    prob_abandono REAL,
                    segmento_riesgo TEXT,
                    accion_retencion TEXT,
                    payload JSONB
                );
                """
            )
            for fila in registros:
                cur.execute(
                    """
                    INSERT INTO ml_predicciones
                        (prob_abandono, segmento_riesgo, accion_retencion, payload)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        fila.get("prob_abandono"),
                        fila.get("segmento_riesgo"),
                        fila.get("accion_retencion"),
                        json.dumps(fila, ensure_ascii=False),
                    ),
                )
        conn.commit()
        destinos["base_datos"] = True
        logger.info("Predicciones insertadas en Neon (tabla ml_predicciones).")
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        logger.warning("No se pudieron guardar predicciones en BD: %s", exc)
    finally:
        conn.close()
    return destinos


def leer_predicciones(limite: int | None = None) -> list[dict]:
    """
    Lee las últimas predicciones. Prioriza ``reports/predicciones.json``;
    si no existe, cae al CSV histórico ``data/clientes_scoreados.csv``.
    """
    if RUTA_PREDICCIONES_JSON.exists():
        data = json.loads(RUTA_PREDICCIONES_JSON.read_text(encoding="utf-8"))
        registros = data.get("predicciones", [])
    elif RUTA_SCOREADOS.exists():
        registros = pd.read_csv(RUTA_SCOREADOS).to_dict(orient="records")
    else:
        registros = []
    if limite is not None:
        return registros[:limite]
    return registros
