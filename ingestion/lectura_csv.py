from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from utils.logger_setup import configurar_logger

logger = configurar_logger(
    "ingestion.lectura_csv", archivo="ingest.log", consola=False
)

RAIZ = Path(__file__).resolve().parents[1]


def leer_datos_csv() -> pd.DataFrame:
    t0 = time.perf_counter()
    source = str(RAIZ / "solicitudes_compra.csv")
    try:
        df = pd.read_csv(source)
        dur_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"proceso=lectura_csv fuente={source} "
            f"filas_entrada=0 filas_salida={len(df)} "
            f"duracion_ms={dur_ms:.1f} status=OK"
        )
        print(f"Solicitudes de compra cargadas: {len(df)}")
        return df
    except Exception as e:
        dur_ms = (time.perf_counter() - t0) * 1000
        logger.error(
            f"proceso=lectura_csv fuente={source} "
            f"filas_entrada=0 filas_salida=0 "
            f"duracion_ms={dur_ms:.1f} status=ERROR error={e}"
        )
        raise
