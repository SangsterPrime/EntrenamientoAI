from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from utils.logger_setup import configurar_logger

RUTA_ENV = Path(__file__).resolve().parents[1] / ".env"
if RUTA_ENV.exists():
    load_dotenv(RUTA_ENV)

RUTA_NEXORA = Path(__file__).resolve().parents[1] / "nexora-ml" / "src"
if RUTA_NEXORA.exists():
    sys.path.insert(0, str(RUTA_NEXORA))
    from seguridad import seudonimizar_id, enmascarar_para_rol, generalizar_edad, puede_exportar
else:
    import hashlib
    import os

    def seudonimizar_id(valor: str | int) -> str:
        sal = os.getenv("NEXORA_SALT", "nexora-demo-salt")
        bruto = f"{sal}:{valor}".encode("utf-8")
        return hashlib.sha256(bruto).hexdigest()[:16]

    def enmascarar_para_rol(df: pd.DataFrame, rol: str) -> pd.DataFrame:
        return df

    def generalizar_edad(edad: int) -> str:
        if edad < 25: return "18-24"
        if edad < 35: return "25-34"
        if edad < 45: return "35-44"
        if edad < 55: return "45-54"
        if edad < 65: return "55-64"
        return "65+"

    def puede_exportar(rol: str) -> bool:
        return True

logger = configurar_logger(
    "security.config", archivo="audit.log", consola=False
)


def log_audit(
    accion: str,
    modulo: str,
    tabla: str,
    filas: int,
    extra: str | None = None,
) -> None:
    msg = (
        f"[AUDIT] [{modulo}] -> "
        f"accion={accion} tabla={tabla} filas={filas}"
    )
    if extra:
        msg += f" {extra}"
    logger.info(msg)


def aplicar_seudonimizacion_rut(almacen_datos: dict) -> dict:
    proveedores = almacen_datos.get("Proveedores")
    if proveedores is not None and "rut" in proveedores.columns:
        n = len(proveedores)
        proveedores["rut_hash"] = proveedores["rut"].apply(seudonimizar_id)
        almacen_datos["Proveedores"] = proveedores
        log_audit(
            "SEUDONIMIZAR",
            "security.config.aplicar_seudonimizacion_rut",
            "proveedores.rut",
            n,
            extra="metodo=SHA256+sal",
        )
        print(f"RUT seudonimizados: {n} proveedores")
    return almacen_datos


def aplicar_enmascaramiento_clientes(
    df: pd.DataFrame,
    rol: str = "analista",
) -> pd.DataFrame:
    t0 = time.perf_counter()
    resultado = enmascarar_para_rol(df, rol)
    dur_ms = (time.perf_counter() - t0) * 1000
    log_audit(
        "ENMASCARAR",
        "security.config.aplicar_enmascaramiento_clientes",
        "clientes_scoreados",
        len(resultado),
        extra=f"rol={rol} duracion_ms={dur_ms:.1f}",
    )
    return resultado
