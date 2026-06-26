"""
NegocIA · Autonomous Procurement Intelligence
Pipeline DataOps unificado (Parcial 2 + Parcial 3).
Flujo completo: ingesta multi-fuente → transformacion → validacion → scoring IA → carga Neon
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

RUTA_NEXORA = Path(__file__).resolve().parent / "nexora-ml" / "src"
if RUTA_NEXORA.exists():
    sys.path.insert(0, str(RUTA_NEXORA))

import pandas as pd

from ingestion.lectura_csv import leer_datos_csv
from ingestion.leer_batch import leer_datos_batch
from ingestion.fuente_realtime import leer_cotizaciones_tiempo_real
from procesamiento.transformacion import generar_transformaciones
from data_quality.validacion import ejecutar_validaciones
from monitoring.kpis import calcular_kpis, imprimir_kpis, guardar_kpis_log
from security.config import aplicar_seudonimizacion_rut, log_audit

from integracion_pipeline import ejecutar_scoring

from carga.cargar_datos import ejecutar_carga


def run_orchestator() -> dict:
    t_inicio = time.perf_counter()

    almacen_datos = {}

    # ========== ETAPA 1: INGESTA ==========
    print("\n========== ETAPA 1: INGESTA MULTI-FUENTE ==========")
    print("--- 1.1 Solicitudes de compra (CSV) ---")
    almacen_datos["Solicitudes"] = leer_datos_csv()

    print("--- 1.2 Catalogo de proveedores (Batch) ---")
    almacen_datos["Proveedores"] = leer_datos_batch()

    print("--- 1.3 Cotizaciones via email (Tiempo real) ---")
    df_cotizaciones = leer_cotizaciones_tiempo_real(5)
    almacen_datos["Cotizaciones_Raw"] = df_cotizaciones.copy()
    almacen_datos["Cotizaciones"] = df_cotizaciones.copy()

    print("\n--- Resumen de datos ingestados ---")
    for elemento, df in almacen_datos.items():
        print(f"\nFUENTE: {elemento}")
        if hasattr(df, "empty") and not df.empty:
            print(f"Filas: {len(df)} | Columnas: {list(df.columns)}")
            print(df.head(2))
        else:
            print("Sin datos")

    # ========== ETAPA 2: TRANSFORMACION ==========
    print("\n========== ETAPA 2: TRANSFORMACION ==========")
    almacen_datos = generar_transformaciones(almacen_datos)

    print("\n--- Resumen de datos transformados ---")
    for elemento, df in almacen_datos.items():
        print(f"\nFUENTE: {elemento}")
        if hasattr(df, "empty") and not df.empty:
            print(df.head(2) if hasattr(df, "head") else df)
        elif isinstance(df, pd.Series):
            print(f"  {df.to_dict()}")
        else:
            print("Sin datos")

    # ========== ETAPA 3: VALIDACION ==========
    print("\n========== ETAPA 3: VALIDACION ==========")
    almacen_datos = ejecutar_validaciones(almacen_datos)

    print("\n--- Resumen de datos validados ---")
    for elemento, df in almacen_datos.items():
        print(f"\nFUENTE: {elemento}")
        if hasattr(df, "empty") and not df.empty:
            print(df.head(2) if hasattr(df, "head") else df)
        elif isinstance(df, pd.Series):
            print(f"  {df.to_dict()}")
        else:
            print("Sin datos")

    # ========== ETAPA 4: SCORING IA (Parcial 3) ==========
    print("\n========== ETAPA 4: SCORING IA (PREDICCION CHURN) ==========")
    almacen_datos = ejecutar_scoring(almacen_datos)

    # ========== SEGURIDAD: seudonimizacion antes de carga ==========
    print("\n========== SEGURIDAD: SEUDONIMIZACION ==========")
    almacen_datos = aplicar_seudonimizacion_rut(almacen_datos)
    log_audit("SEUDONIMIZACION", "security.config", "proveedores.rut",
              len(almacen_datos.get("Proveedores", pd.DataFrame())))

    # ========== ETAPA 5: CARGA Neon ==========
    print("\n========== ETAPA 5: CARGA NEON (PostgreSQL) ==========")
    almacen_datos = ejecutar_carga(almacen_datos)

    # ========== KPIs de Monitoreo ==========
    print("\n" + "=" * 70)
    print("RESUMEN DE KPIs — NEGOCIA PIPELINE UNIFICADO")
    print("=" * 70)
    kpis = calcular_kpis(almacen_datos)
    imprimir_kpis(kpis)
    guardar_kpis_log(kpis)

    t_total = time.perf_counter() - t_inicio
    log_audit("PIPELINE_COMPLETO", "pipeline.run_orchestator",
              "todas", sum(len(v) for v in almacen_datos.values()
                          if hasattr(v, "__len__") and not isinstance(v, str)),
              extra=f"duracion_total_s={t_total:.3f}")

    print(f"\nPipeline NegocIA completado en {t_total:.3f} segundos.")
    return almacen_datos


if __name__ == "__main__":
    results = run_orchestator()
