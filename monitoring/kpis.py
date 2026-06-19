from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from utils.logger_setup import configurar_logger

RAIZ = Path(__file__).resolve().parents[1]
RUTA_METRICAS_JSON = RAIZ / "nexora-ml" / "reports" / "metricas.json"
RUTA_CLIENTES_SCOREADOS = RAIZ / "nexora-ml" / "data" / "clientes_scoreados.csv"

logger = configurar_logger(
    "monitoring.kpis", archivo="kpis.log", consola=False
)

UMBRALES_ALERTAS = {
    "completitud_datos":        (90.0,  80.0,  "Completitud de datos (%)",         "min"),
    "tasa_parsing_exitoso":     (85.0,  70.0,  "Tasa parsing exitoso (%)",         "min"),
    "errores_validacion":       (3,     10,    "Errores de validacion (N)",        "max"),
    "disponibilidad_api":       (None,  None,  "Disponibilidad API cotizaciones",  "bool"),
    "filas_cargadas_neon":      (1,     0,     "Filas Cargadas Neon",              "min"),
    "latencia_ingesta_ms":      (5000,  30000, "Latencia de ingesta (ms)",         "max"),
    "recall_modelo":            (0.50,  0.30,  "Recall del modelo churn",          "min"),
    "clientes_alto_riesgo":     (200,   300,   "Clientes en riesgo ALTO",          "max"),
    "tasa_respuesta_proveedores": (60.0, 40.0, "Tasa respuesta proveedores (%)",   "min"),
    "rondas_negociacion_prom":  (4,     6,     "Rondas negociacion promedio",      "max"),
}


def _leer_metricas_json() -> dict:
    ruta = RUTA_METRICAS_JSON
    if ruta.exists():
        try:
            import json
            return json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _contar_segmentos() -> dict:
    ruta = RUTA_CLIENTES_SCOREADOS
    if ruta.exists():
        try:
            df = pd.read_csv(ruta)
            conteo = df["segmento_riesgo"].value_counts().to_dict()
            return conteo
        except Exception:
            return {}
    return {}


def calcular_kpis(almacen_datos: dict | None = None) -> dict:
    if almacen_datos is None:
        almacen_datos = {}

    kpis = {}

    solicitudes = almacen_datos.get("Solicitudes", pd.DataFrame())
    if not solicitudes.empty:
        nulos = solicitudes.isna().sum().sum()
        total = solicitudes.shape[0] * solicitudes.shape[1]
        kpis["completitud_datos"] = round((1 - nulos / max(total, 1)) * 100, 2)
    else:
        kpis["completitud_datos"] = 0.0

    cotizaciones = almacen_datos.get("Cotizaciones", pd.DataFrame())
    cotizaciones_raw = almacen_datos.get("Cotizaciones_Raw", pd.DataFrame())
    if not cotizaciones_raw.empty and len(cotizaciones_raw) > 0:
        kpis["tasa_parsing_exitoso"] = round(
            (len(cotizaciones) / len(cotizaciones_raw)) * 100, 2
        )
    else:
        kpis["tasa_parsing_exitoso"] = 100.0

    validas = cotizaciones.get("precio_valido", pd.Series([True])).sum() if not cotizaciones.empty else 0
    total_cot = len(cotizaciones) if not cotizaciones.empty else 1
    kpis["errores_validacion"] = total_cot - validas

    kpis["disponibilidad_api"] = len(cotizaciones) >= 1

    resumen_carga = almacen_datos.get("Resumen_Carga", {})
    kpis["filas_cargadas_neon"] = resumen_carga.get("total_filas_insertadas", 0)
    kpis["latencia_ingesta_ms"] = resumen_carga.get("duracion_s", 0) * 1000

    metricas_json = _leer_metricas_json()
    kpis["modelo_activo"] = metricas_json.get("modelo_seleccionado", "No disponible")
    metricas_modelo = metricas_json.get("metricas_por_modelo", {})
    modelo_activo = kpis["modelo_activo"]
    if modelo_activo in metricas_modelo:
        m = metricas_modelo[modelo_activo]
        kpis["recall_modelo"] = m.get("recall", 0.0)
        kpis["gini_modelo"] = m.get("gini", 0.0)
    else:
        kpis["recall_modelo"] = 0.0
        kpis["gini_modelo"] = 0.0

    segmentos = _contar_segmentos()
    kpis["clientes_alto_riesgo"] = segmentos.get("ALTO", 0)
    total_clientes = sum(segmentos.values())
    kpis["tasa_riesgo_alto"] = round(
        (segmentos.get("ALTO", 0) / max(total_clientes, 1)) * 100, 2
    )

    if not cotizaciones.empty and "proveedor_id" in cotizaciones.columns:
        proveedores_unicos = cotizaciones["proveedor_id"].nunique()
        kpis["tasa_respuesta_proveedores"] = round(
            (proveedores_unicos / 10) * 100, 1
        )
    else:
        kpis["tasa_respuesta_proveedores"] = 0.0

    negociaciones = almacen_datos.get("Negociaciones", pd.DataFrame())
    if not negociaciones.empty and "ronda" in negociaciones.columns:
        kpis["rondas_negociacion_prom"] = round(negociaciones["ronda"].mean(), 1)
    else:
        kpis["rondas_negociacion_prom"] = 0.0

    kpis["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return kpis


def evaluar_alertas(kpis: dict) -> list[dict]:
    alertas = []
    for key, (warn, crit, label, direccion) in UMBRALES_ALERTAS.items():
        valor = kpis.get(key)
        if valor is None:
            continue

        if direccion == "bool":
            if not valor:
                alertas.append({
                    "key": key, "valor": valor, "nivel": "CRITICAL",
                    "mensaje": f"{label} = {valor} — API no disponible"
                })
            continue

        if direccion == "max":
            if crit is not None and valor >= crit:
                alertas.append({
                    "key": key, "valor": valor, "nivel": "CRITICAL",
                    "mensaje": f"{label} = {valor} (umbral critico: <={crit})"
                })
            elif warn is not None and valor >= warn:
                alertas.append({
                    "key": key, "valor": valor, "nivel": "WARNING",
                    "mensaje": f"{label} = {valor} (umbral warning: <={warn})"
                })
        elif direccion == "min":
            if crit is not None and valor <= crit:
                alertas.append({
                    "key": key, "valor": valor, "nivel": "CRITICAL",
                    "mensaje": f"{label} = {valor} (umbral critico: >={crit})"
                })
            elif warn is not None and valor <= warn:
                alertas.append({
                    "key": key, "valor": valor, "nivel": "WARNING",
                    "mensaje": f"{label} = {valor} (umbral warning: >={warn})"
                })
    return alertas


def imprimir_kpis(kpis: dict) -> None:
    alertas = evaluar_alertas(kpis)

    print("\n" + "-" * 70)
    print(f"  KPI Report — NegocIA — {kpis.get('timestamp', 'N/A')}")
    print("-" * 70)
    print(f"  {'Indicador':<40} {'Valor':>20}")
    print("  " + "-" * 62)
    for key, val in kpis.items():
        if key == "timestamp":
            continue
        label = key.replace("_", " ").title()
        print(f"  {label:<40} {str(val):>20}")
    print("-" * 70)

    if alertas:
        print("\n  [!] ALERTAS ACTIVAS:")
        for a in alertas:
            icono = "[CRITICAL]" if a["nivel"] == "CRITICAL" else "[WARN]"
            print(f"  {icono} [{a['nivel']}] {a['mensaje']}")
        print("-" * 70)


def guardar_kpis_log(kpis: dict) -> None:
    alertas = evaluar_alertas(kpis)

    logger.info("=" * 60)
    logger.info("KPI REPORT · NegocIA · Pipeline DataOps + IA")
    for key, val in kpis.items():
        if key == "timestamp":
            continue
        logger.info(f"  {key}: {val}")

    if alertas:
        for a in alertas:
            if a["nivel"] == "CRITICAL":
                logger.error(f"  ALERTA [{a['nivel']}] {a['mensaje']}")
            else:
                logger.warning(f"  ALERTA [{a['nivel']}] {a['mensaje']}")
    logger.info("=" * 60)
