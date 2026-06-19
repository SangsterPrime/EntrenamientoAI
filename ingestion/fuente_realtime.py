from __future__ import annotations

import random
import time
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from utils.logger_setup import configurar_logger

logger = configurar_logger(
    "ingestion.fuente_realtime", archivo="ingest.log", consola=False
)


PROVEEDORES = [
    (1, "Distribuidora Santiago Ltda."),
    (2, "Insumos Industriales Chile SPA"),
    (3, "Proveedora Nacional del Sur"),
    (4, "Comercial del Pacifico Ltda."),
    (5, "Suministros Tecnologicos SPA"),
    (6, "Logistica y Abastecimiento SA"),
    (7, "Materiales de Construccion RML"),
    (8, "Oficina Total Express Ltda."),
    (9, "NetCloud Solutions Spa"),
    (10, "Seguridad Integral Chile SA"),
]

PRODUCTOS = [
    "Laptops empresariales", "Resmas de papel carta", "Toner para impresora HP",
    "Sillas ergonomicas", "Servidor NAS 12TB", "Escritorios modulares",
    "Licencias Microsoft 365", "Cables de red CAT6", "Monitores 27 pulgadas",
    "Extinguidores ABC 10kg", "Router corporativo gigabit", "Papel higienico industrial",
    "Camaras de seguridad IP", "Software antivirus corporativo", "Mesas de reuniones",
]


def _generar_cotizacion() -> dict:
    proveedor_id, nombre = random.choice(PROVEEDORES)
    producto = random.choice(PRODUCTOS)
    precio_base = random.uniform(50000, 2500000)
    precio_total = round(precio_base * random.uniform(1, 50), 2)
    plazo_dias = random.choice([2, 3, 5, 7, 10, 14, 15, 20, 25, 30])
    garantia_meses = random.choice([0, 6, 12, 18, 24, 36])
    risk_score = round(random.uniform(0, 40), 1)
    return {
        "proveedor_id": proveedor_id,
        "proveedor_nombre": nombre,
        "producto": producto,
        "precio_total": precio_total,
        "plazo_dias": plazo_dias,
        "garantia_meses": garantia_meses,
        "risk_score": risk_score,
        "email_asunto": f"Cotizacion: {producto}",
        "timestamp": datetime.now().isoformat(),
    }


def leer_cotizaciones_tiempo_real(n_snapshots: int = 5) -> pd.DataFrame:
    t0 = time.perf_counter()
    registros = []
    for i in range(n_snapshots):
        registro = _generar_cotizacion()
        registros.append(registro)
        latencia_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"proceso=cotizacion_realtime snapshot={i+1} "
            f"proveedor={registro['proveedor_id']} producto={registro['producto']} "
            f"precio={registro['precio_total']} duracion_ms={latencia_ms:.1f} status=OK"
        )
        if i < n_snapshots - 1:
            time.sleep(0.5)

    df = pd.DataFrame(registros)
    dur_total = (time.perf_counter() - t0) * 1000
    logger.info(
        f"proceso=leer_cotizaciones_realtime "
        f"filas_entrada=0 filas_salida={len(df)} "
        f"duracion_ms={dur_total:.1f} status=OK"
    )
    print(f"Cotizaciones recibidas via email (simulacion): {len(df)}")
    return df
