"""
NEXORA · Integración del modelo de IA al pipeline DataOps (Parcial 2 → 3)
========================================================================
integracion_pipeline.py — Demuestra cómo el módulo de Inteligencia Predictiva
se acopla al pipeline DataOps existente (ingesta → procesamiento → validación
→ carga) como una NUEVA ETAPA de "scoring", sin romper el flujo original.

Esta es la "mejora/optimización del pipeline" exigida por la rúbrica del
Parcial 3: el pipeline ahora no sólo gestiona datos, sino que los enriquece
con una predicción de abandono para accionar retención.

Flujo de la nueva etapa:
    1. Ingesta de la cartera de clientes (CSV → simula extracción desde la BD).
    2. Validación de calidad mínima (reusa data_quality del Parcial 2).
    3. Scoring: el modelo entrenado asigna probabilidad de abandono a cada cliente.
    4. Segmentación de riesgo (Alto / Medio / Bajo) para el equipo de retención.
    5. Carga del resultado scoreado a un CSV/tabla (simula UPSERT en PostgreSQL).
    6. Logging de la ejecución para evidencia de rendimiento en nube.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import joblib
import pandas as pd

import preprocesamiento as prep

RAIZ = Path(__file__).resolve().parents[1]
DIR_MODELOS = RAIZ / "models"
DIR_PROC = RAIZ / "data"
DIR_LOGS = RAIZ / "logs"
DIR_PROC.mkdir(parents=True, exist_ok=True)
DIR_LOGS.mkdir(parents=True, exist_ok=True)

# --- Logging de la etapa de scoring -----------------------------------------
logger = logging.getLogger("nexora.scoring")
logger.setLevel(logging.INFO)
logger.handlers.clear()
_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
_fh = logging.FileHandler(DIR_LOGS / "scoring_pipeline.log", encoding="utf-8")
_fh.setFormatter(_fmt)
_ch = logging.StreamHandler()
_ch.setFormatter(_fmt)
logger.addHandler(_fh)
logger.addHandler(_ch)


def cargar_modelo():
    """Carga el paquete de modelo entrenado (artefacto local confiable)."""
    ruta = DIR_MODELOS / "modelo_churn.pkl"
    if not ruta.exists():
        raise FileNotFoundError(
            "No existe models/modelo_churn.pkl. Ejecuta primero src/entrenamiento.py"
        )
    return joblib.load(ruta)


def segmentar_riesgo(proba: float) -> str:
    """Traduce la probabilidad en un segmento accionable para retención."""
    if proba >= 0.60:
        return "ALTO"
    if proba >= 0.35:
        return "MEDIO"
    return "BAJO"


def ejecutar_scoring(almacen_datos: dict | None = None) -> dict:
    """
    Nueva etapa del pipeline DataOps: aplica el modelo de IA sobre la cartera
    de clientes y devuelve el almacén de datos enriquecido con el scoring.

    Acepta el mismo patrón 'almacen_datos' (dict de DataFrames) del pipeline
    del Parcial 2, de modo que puede insertarse en pipeline.py sin fricción.
    """
    t0 = time.perf_counter()
    logger.info("=" * 60)
    logger.info("Etapa de SCORING IA · inicio")

    almacen_datos = almacen_datos or {}

    # 1. Ingesta de la cartera (en producción: SELECT desde tabla 'clientes')
    if "Clientes" in almacen_datos and isinstance(almacen_datos["Clientes"], pd.DataFrame):
        cartera = almacen_datos["Clientes"].copy()
        logger.info(f"Cartera recibida del almacén: {len(cartera)} clientes")
    else:
        cartera = prep.cargar_datos()
        logger.info(f"Cartera ingestada desde CSV: {len(cartera)} clientes")

    # 2. Validación de calidad mínima (reusa lógica del Parcial 2)
    calidad = prep.analisis_calidad(cartera)
    if calidad["total_nulos"] > 0:
        logger.warning(f"Se detectaron {calidad['total_nulos']} nulos; se imputan.")
    cartera = prep.imputar_nulos(cartera)

    # 3. Scoring con el modelo entrenado
    paquete = cargar_modelo()
    columnas = paquete["columnas"]
    X = cartera[columnas]
    if paquete.get("requiere_escalado"):
        X = paquete["scaler"].transform(X)
    proba = paquete["modelo"].predict_proba(X)[:, 1]

    cartera_scored = cartera.copy()
    cartera_scored["prob_abandono"] = proba.round(4)
    cartera_scored["segmento_riesgo"] = [segmentar_riesgo(p) for p in proba]
    cartera_scored["accion_retencion"] = cartera_scored["segmento_riesgo"].map({
        "ALTO": "Contacto prioritario + oferta de retención",
        "MEDIO": "Campaña de fidelización automatizada",
        "BAJO": "Monitoreo estándar",
    })

    # 4. Resumen de segmentación
    resumen = cartera_scored["segmento_riesgo"].value_counts().to_dict()
    logger.info(f"Segmentación de riesgo: {resumen}")

    # 5. Carga del resultado (en producción: UPSERT a PostgreSQL)
    ruta_salida = DIR_PROC / "clientes_scoreados.csv"
    cartera_scored.to_csv(ruta_salida, index=False, encoding="utf-8")
    logger.info(f"Resultado scoreado persistido en {ruta_salida}")

    dur = time.perf_counter() - t0
    logger.info(f"Etapa de SCORING IA · fin ({dur:.3f}s, modelo={paquete['nombre_modelo']})")
    logger.info("=" * 60)

    almacen_datos["Clientes_Scoreados"] = cartera_scored
    almacen_datos["Resumen_Riesgo"] = pd.Series(resumen, name="clientes")
    return almacen_datos


if __name__ == "__main__":
    resultado = ejecutar_scoring()
    scored = resultado["Clientes_Scoreados"]
    print("\nTop 5 clientes en mayor riesgo de abandono:")
    cols = ["edad", "anos_cliente", "reclamos", "plan_premium",
            "prob_abandono", "segmento_riesgo", "accion_retencion"]
    print(scored.sort_values("prob_abandono", ascending=False)[cols].head(5).to_string(index=False))
    print("\nDistribución por segmento:")
    print(resultado["Resumen_Riesgo"].to_string())
