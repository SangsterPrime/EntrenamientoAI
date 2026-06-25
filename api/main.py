"""
NEXORA · API REST de Inteligencia Predictiva (FastAPI)
======================================================
api/main.py — Expone el módulo de IA (entrenamiento + scoring de churn) como un
servicio web desplegable en Render, sin romper la ejecución batch/local del
pipeline (`python pipeline.py`).

Endpoints
---------
    GET  /health       Estado del servicio (modelo, BD, entorno).
    POST /train        Entrena el modelo, genera métricas, matriz de confusión,
                       curva ROC, Gini, figuras y persiste reportes.
    POST /score        Scoring/predicción con el modelo entrenado (online o batch).
    GET  /metrics      Últimas métricas del modelo en JSON.
    GET  /predictions  Últimas predicciones / clientes scoreados.

Seguridad
---------
    Si la variable de entorno ML_API_KEY está definida, los endpoints que
    ejecutan cómputo (POST /train, POST /score) exigen la cabecera
    ``X-API-Key``. Si no está definida (desarrollo local), quedan abiertos.
    Nunca hay credenciales embebidas: todo proviene del entorno / .env.

Ejecución local
---------------
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# --- Rutas y carga de entorno ------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
RUTA_NEXORA_SRC = RAIZ / "nexora-ml" / "src"
DIR_LOGS = RAIZ / "nexora-ml" / "logs"
DIR_MODELOS = RAIZ / "nexora-ml" / "models"
DIR_LOGS.mkdir(parents=True, exist_ok=True)

# El módulo IA (entrenamiento, scoring, persistencia) vive en nexora-ml/src y
# se importa por nombre, igual que en pipeline.py.
if str(RUTA_NEXORA_SRC) not in sys.path:
    sys.path.insert(0, str(RUTA_NEXORA_SRC))

_dotenv = RAIZ / ".env"
if _dotenv.exists():
    load_dotenv(_dotenv)

ENTORNO = os.getenv("ENVIRONMENT", "local")
RUTA_MODELO = DIR_MODELOS / "modelo_churn.pkl"

# --- Logging de la API (archivo + consola) con tiempos de ejecución ----------
logger = logging.getLogger("nexora.api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _fmt = logging.Formatter("[%(asctime)s] - [%(levelname)s] - [nexora.api] -> %(message)s",
                             datefmt="%Y-%m-%d %H:%M:%S")
    _fh = logging.FileHandler(DIR_LOGS / "api.log", encoding="utf-8")
    _fh.setFormatter(_fmt)
    _ch = logging.StreamHandler(sys.stdout)
    _ch.setFormatter(_fmt)
    logger.addHandler(_fh)
    logger.addHandler(_ch)


# --- Aplicación --------------------------------------------------------------
app = FastAPI(
    title="NEXORA · Inteligencia Predictiva API",
    description="Servicio de entrenamiento y scoring de churn (Evaluación Parcial 3).",
    version="1.0.0",
)


@app.middleware("http")
async def registrar_tiempo(request: Request, call_next):
    """Log de rendimiento por solicitud (evidencia de ejecución nube/local)."""
    t0 = time.perf_counter()
    respuesta = await call_next(request)
    dur_ms = (time.perf_counter() - t0) * 1000
    respuesta.headers["X-Process-Time-ms"] = f"{dur_ms:.1f}"
    logger.info(f"{request.method} {request.url.path} -> {respuesta.status_code} ({dur_ms:.1f} ms)")
    return respuesta


# --- Seguridad: verificación opcional de API key -----------------------------
def verificar_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    esperada = os.getenv("ML_API_KEY")
    if esperada:  # solo se exige si está configurada en el entorno
        if not x_api_key or x_api_key != esperada:
            raise HTTPException(status_code=401, detail="API key inválida o ausente (X-API-Key).")


# --- Esquemas de entrada/salida ----------------------------------------------
class ClienteInput(BaseModel):
    """Perfil de un cliente para el scoring online (mismas variables del modelo)."""
    edad: int = Field(..., ge=18, le=99, examples=[45])
    anos_cliente: int = Field(..., ge=0, examples=[5])
    uso_datos_gb: float = Field(..., ge=0, examples=[10.5])
    llamadas_mes: int = Field(..., ge=0, examples=[47])
    reclamos: int = Field(..., ge=0, examples=[2])
    plan_premium: int = Field(..., ge=0, le=1, examples=[0])


class ScoreRequest(BaseModel):
    """
    Cuerpo opcional de POST /score.

    - Con ``clientes``: scoring online sobre los perfiles enviados.
    - Sin cuerpo (o ``clientes`` vacío): scoring batch sobre la cartera del CSV.
    """
    clientes: list[ClienteInput] | None = None


def _modelo_entrenado() -> bool:
    return RUTA_MODELO.exists()


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Endpoints ---------------------------------------------------------------
@app.get("/health", tags=["estado"])
def health() -> dict:
    """Estado del servicio: entorno, disponibilidad del modelo y de la BD."""
    try:
        from persistencia import resolver_database_url

        bd_configurada = resolver_database_url() is not None
    except Exception:  # noqa: BLE001
        bd_configurada = False

    return {
        "status": "ok",
        "servicio": "NEXORA · Inteligencia Predictiva",
        "version": app.version,
        "entorno": ENTORNO,
        "modelo_entrenado": _modelo_entrenado(),
        "base_datos_configurada": bd_configurada,
        "timestamp": _ahora(),
    }


@app.post("/train", tags=["modelo"], dependencies=[Depends(verificar_api_key)])
def train() -> dict:
    """
    Ejecuta el entrenamiento completo del modelo de IA.

    Genera y persiste: métricas (accuracy, precision, recall, F1, ROC-AUC, Gini),
    matriz de confusión, curva ROC, comparación de modelos, importancia de
    variables, el modelo serializado y logs de rendimiento.
    """
    t0 = time.perf_counter()
    logger.info("POST /train · inicio del entrenamiento")
    try:
        import entrenamiento
        import persistencia
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error importando el módulo de entrenamiento")
        raise HTTPException(status_code=500, detail=f"Error de importación: {exc}") from exc

    try:
        resumen = entrenamiento.main()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo durante el entrenamiento")
        raise HTTPException(status_code=500, detail=f"Fallo en entrenamiento: {exc}") from exc

    # Persistencia centralizada (reports/ + BD opcional).
    destinos = persistencia.guardar_metricas(resumen)

    dur = time.perf_counter() - t0
    logger.info(f"POST /train · fin ({dur:.3f}s, modelo={resumen.get('modelo_seleccionado')})")
    return {
        "status": "entrenado",
        "modelo_seleccionado": resumen.get("modelo_seleccionado"),
        "metricas_modelo": resumen.get("metricas_por_modelo", {}).get(
            resumen.get("modelo_seleccionado"), {}
        ),
        "tiempo_entrenamiento_s": round(dur, 3),
        "persistencia": destinos,
        "timestamp": _ahora(),
    }


@app.post("/score", tags=["modelo"], dependencies=[Depends(verificar_api_key)])
def score(payload: ScoreRequest | None = None) -> dict:
    """
    Scoring/predicción con el modelo entrenado.

    - Si se envían ``clientes``: predicción online de esos perfiles.
    - Si no: scoring batch sobre la cartera del dataset y persistencia a reports/.
    """
    if not _modelo_entrenado():
        raise HTTPException(
            status_code=409,
            detail="No hay modelo entrenado. Ejecuta primero POST /train.",
        )

    t0 = time.perf_counter()
    try:
        import integracion_pipeline as ip
        import persistencia
        import pandas as pd
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error importando el módulo de scoring")
        raise HTTPException(status_code=500, detail=f"Error de importación: {exc}") from exc

    try:
        if payload and payload.clientes:
            # --- Scoring ONLINE (perfiles enviados en la solicitud) ----------
            df = pd.DataFrame([c.model_dump() for c in payload.clientes])
            scored = ip.puntuar_dataframe(df)
            destinos = persistencia.guardar_predicciones(scored)
            modo = "online"
            registros = scored.to_dict(orient="records")
            resumen = scored["segmento_riesgo"].value_counts().to_dict()
        else:
            # --- Scoring BATCH (cartera completa del pipeline) ---------------
            resultado = ip.ejecutar_scoring()
            scored = resultado["Clientes_Scoreados"]
            destinos = {"archivo_json": "reports/predicciones.json", "centralizado": True}
            modo = "batch"
            registros = scored.head(20).to_dict(orient="records")
            resumen = resultado["Resumen_Riesgo"].to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo durante el scoring")
        raise HTTPException(status_code=500, detail=f"Fallo en scoring: {exc}") from exc

    dur = time.perf_counter() - t0
    logger.info(f"POST /score · modo={modo} filas={len(scored)} ({dur:.3f}s)")
    return {
        "status": "scoreado",
        "modo": modo,
        "total": int(len(scored)),
        "resumen_riesgo": resumen,
        "predicciones": registros,
        "persistencia": destinos,
        "tiempo_scoring_s": round(dur, 3),
        "timestamp": _ahora(),
    }


@app.get("/metrics", tags=["reportes"])
def metrics() -> dict:
    """Devuelve las últimas métricas del modelo (reports/metricas.json)."""
    try:
        import persistencia

        data = persistencia.leer_metricas()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error leyendo métricas: {exc}") from exc
    if not data:
        raise HTTPException(
            status_code=404,
            detail="No hay métricas disponibles. Ejecuta primero POST /train.",
        )
    return data


@app.get("/predictions", tags=["reportes"])
def predictions(limite: int = 50) -> dict:
    """Devuelve las últimas predicciones / clientes scoreados."""
    try:
        import persistencia

        registros = persistencia.leer_predicciones(limite=limite)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error leyendo predicciones: {exc}") from exc
    if not registros:
        raise HTTPException(
            status_code=404,
            detail="No hay predicciones disponibles. Ejecuta primero POST /score.",
        )
    return {"total": len(registros), "predicciones": registros, "timestamp": _ahora()}


@app.get("/", tags=["estado"])
def raiz() -> JSONResponse:
    """Punto de entrada con el catálogo de endpoints."""
    return JSONResponse(
        {
            "servicio": "NEXORA · Inteligencia Predictiva API",
            "docs": "/docs",
            "endpoints": ["/health", "/train", "/score", "/metrics", "/predictions"],
        }
    )
