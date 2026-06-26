"""
NEXORA · Cron Job batch (Render Cron Job)
=========================================
cron_job.py — Ejecución batch del flujo de IA pensada para correr como
**Render Cron Job**: lanza un comando, entrena, puntúa, persiste y termina con
un código de salida claro. No levanta servidor HTTP ni depende de uvicorn.

Flujo:
    1. Entrenamiento del modelo (entrenamiento.main).
    2. Persistencia de métricas (persistencia.guardar_metricas).
    3. Scoring batch de la cartera (integracion_pipeline.ejecutar_scoring).
    4. Persistencia de predicciones (persistencia.guardar_predicciones).

Persistencia: siempre escribe en ``nexora-ml/reports`` (JSON/CSV) y, si existe
``DATABASE_URL`` (o ``DB_URL`` / ``NEON_DATABASE_URL``), también en las tablas
Neon ``ml_metricas`` / ``ml_predicciones``.

Códigos de salida:
    0  → todo el flujo terminó correctamente.
    1  → falló alguna etapa (queda registrado en el log).

Ejecución:
    python cron_job.py

El modo API (api/main.py + uvicorn) sigue disponible y es independiente de este
script: el proyecto soporta dos modos (cron batch para producción y API para demo).

Sin credenciales hardcodeadas ni rutas absolutas: todo se resuelve relativo al
proyecto y los secretos provienen del entorno / .env.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# --- Rutas y entorno ---------------------------------------------------------
RAIZ = Path(__file__).resolve().parent
RUTA_NEXORA_SRC = RAIZ / "nexora-ml" / "src"
DIR_LOGS = RAIZ / "nexora-ml" / "logs"
DIR_LOGS.mkdir(parents=True, exist_ok=True)

# El módulo IA vive en nexora-ml/src y se importa por nombre (igual que en
# pipeline.py y api/main.py). Mantener este patrón.
if str(RUTA_NEXORA_SRC) not in sys.path:
    sys.path.insert(0, str(RUTA_NEXORA_SRC))

_dotenv = RAIZ / ".env"
if _dotenv.exists():
    load_dotenv(_dotenv)

ENTORNO = os.getenv("ENVIRONMENT", "local")

# --- Logging (archivo + consola) ---------------------------------------------
logger = logging.getLogger("nexora.cron")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _fmt = logging.Formatter(
        "[%(asctime)s] - [%(levelname)s] - [nexora.cron] -> %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _fh = logging.FileHandler(DIR_LOGS / "cron.log", encoding="utf-8")
    _fh.setFormatter(_fmt)
    _ch = logging.StreamHandler(sys.stdout)
    _ch.setFormatter(_fmt)
    logger.addHandler(_fh)
    logger.addHandler(_ch)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def ejecutar() -> int:
    """Orquesta el flujo batch completo. Devuelve el código de salida (0/1)."""
    t_inicio = time.perf_counter()
    logger.info("=" * 70)
    logger.info("NEXORA · Cron Job batch — INICIO")
    logger.info(f"Entorno: {ENTORNO} | timestamp: {_ahora()}")

    # --- Importación del módulo de IA ----------------------------------------
    try:
        import entrenamiento
        import integracion_pipeline as ip
        import persistencia
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"No se pudo importar el módulo de IA: {exc}")
        return 1

    bd_url = persistencia.resolver_database_url()
    logger.info(f"Base de datos configurada: {'sí' if bd_url else 'no'} "
                "(escritura en Neon solo si hay DATABASE_URL)")

    # --- 1. Entrenamiento ----------------------------------------------------
    try:
        t0 = time.perf_counter()
        resumen = entrenamiento.main()
        dur_train = time.perf_counter() - t0
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Fallo en el ENTRENAMIENTO: {exc}")
        return 1

    modelo = resumen.get("modelo_seleccionado", "—")
    met = resumen.get("metricas_por_modelo", {}).get(modelo, {})
    logger.info(f"ENTRENAMIENTO OK en {dur_train:.3f}s | modelo seleccionado: {modelo}")
    logger.info(
        "Métricas principales: "
        f"accuracy={met.get('accuracy')} precision={met.get('precision')} "
        f"recall={met.get('recall')} f1={met.get('f1')} "
        f"roc_auc={met.get('roc_auc')} gini={met.get('gini')}"
    )

    # --- 2. Persistencia de métricas -----------------------------------------
    try:
        destinos_met = persistencia.guardar_metricas(resumen)
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Fallo al PERSISTIR MÉTRICAS: {exc}")
        return 1
    logger.info(
        f"MÉTRICAS persistidas en reports/metricas.json "
        f"| Neon: {'sí' if destinos_met.get('base_datos') else 'no'}"
    )
    if destinos_met.get("error_base_datos"):
        logger.warning(f"Neon métricas falló: {destinos_met['error_base_datos']}")

    # --- 3. Scoring batch ----------------------------------------------------
    # persistir=False: el cron es el dueño explícito de la persistencia de
    # predicciones (paso 4), para no insertar dos veces en Neon en una corrida.
    try:
        t0 = time.perf_counter()
        almacen = ip.ejecutar_scoring(persistir=False)
        dur_score = time.perf_counter() - t0
    except FileNotFoundError as exc:
        logger.exception(f"No hay modelo para SCORING (entrena primero): {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Fallo en el SCORING batch: {exc}")
        return 1

    scored = almacen["Clientes_Scoreados"]
    resumen_riesgo = almacen["Resumen_Riesgo"].to_dict()
    logger.info(
        f"SCORING OK en {dur_score:.3f}s | {len(scored)} predicciones generadas "
        f"| segmentos: {resumen_riesgo}"
    )

    # --- 4. Persistencia de predicciones -------------------------------------
    try:
        destinos_pred = persistencia.guardar_predicciones(scored)
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Fallo al PERSISTIR PREDICCIONES: {exc}")
        return 1
    logger.info(
        f"PREDICCIONES persistidas: {destinos_pred.get('filas')} filas en "
        f"reports/predicciones.(json|csv) "
        f"| Neon: {'sí' if destinos_pred.get('base_datos') else 'no'}"
    )
    if destinos_pred.get("error_base_datos"):
        logger.warning(f"Neon predicciones falló: {destinos_pred['error_base_datos']}")

    # --- Cierre --------------------------------------------------------------
    dur_total = time.perf_counter() - t_inicio
    logger.info(
        f"Cron Job COMPLETADO en {dur_total:.3f}s "
        f"(entrenamiento {dur_train:.3f}s + scoring {dur_score:.3f}s)"
    )
    logger.info("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        codigo = ejecutar()
    except Exception as exc:  # noqa: BLE001 — red de seguridad final
        logger.exception(f"Cron Job ABORTADO por error inesperado: {exc}")
        codigo = 1
    sys.exit(codigo)
