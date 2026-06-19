from __future__ import annotations

import re
import time

import pandas as pd

from utils.logger_setup import configurar_logger

logger = configurar_logger(
    "data_quality.validacion", archivo="validation.log", consola=False
)


def _es_rut_valido(rut: str) -> bool:
    if pd.isna(rut):
        return False
    return bool(re.match(r"^\d{1,2}\.\d{3}\.\d{3}[-][0-9Kk]$", str(rut).strip()))


def _precio_en_rango(precio: float, producto: str) -> bool:
    rangos = {
        "Laptops": (100000, 150000000),
        "Resmas": (100, 10000000),
        "Toner": (1000, 50000000),
        "Sillas": (10000, 100000000),
        "Servidor": (100000, 100000000),
        "Escritorios": (10000, 100000000),
        "Licencias": (5000, 100000000),
        "Cables": (100, 10000000),
        "Monitores": (50000, 100000000),
        "Extinguidores": (1000, 20000000),
        "Router": (10000, 50000000),
        "Papel": (100, 1000000),
        "Camaras": (10000, 50000000),
        "Antivirus": (5000, 50000000),
        "Mesas": (50000, 100000000),
    }
    for clave, (min_p, max_p) in rangos.items():
        if clave.lower() in str(producto).lower():
            return min_p <= precio <= max_p
    return True


def ejecutar_validaciones(almacen_datos: dict) -> dict:
    t0 = time.perf_counter()

    print("Validacion de RUT de proveedores")
    if "Proveedores" in almacen_datos and not almacen_datos["Proveedores"].empty:
        df_prov = almacen_datos["Proveedores"].copy()
        filas_entrada = len(df_prov)
        df_prov["rut_valido"] = df_prov["rut"].apply(_es_rut_valido)
        validos = int(df_prov["rut_valido"].sum())
        logger.info(
            f"proceso=validar_rut columna=rut "
            f"filas_entrada={filas_entrada} ruts_validos={validos} status=OK"
        )
        print(f"RUT validados: {validos}/{filas_entrada} proveedores")
    else:
        logger.warning("proceso=validar_rut status=WARNING error=no_hay_proveedores")

    print("Validacion de rangos de precio en cotizaciones")
    if "Cotizaciones" in almacen_datos and not almacen_datos["Cotizaciones"].empty:
        df_cot = almacen_datos["Cotizaciones"].copy()
        filas_entrada = len(df_cot)
        df_cot["precio_valido"] = df_cot.apply(
            lambda r: _precio_en_rango(r["precio_total"], r.get("producto", "")), axis=1
        )
        validos = int(df_cot["precio_valido"].sum())
        logger.info(
            f"proceso=validar_precios columna=precio_total "
            f"filas_entrada={filas_entrada} precios_validos={validos} status=OK"
        )
        print(f"Precios validados: {validos}/{filas_entrada} cotizaciones")

    print("Asignacion de risk score a cotizaciones")
    if "Cotizaciones" in almacen_datos and not almacen_datos["Cotizaciones"].empty:
        df_cot = almacen_datos["Cotizaciones"]
        if "risk_score" in df_cot.columns:
            df_cot["nivel_riesgo"] = pd.cut(
                df_cot["risk_score"],
                bins=[-1, 10, 25, 100],
                labels=["Bajo", "Medio", "Alto"],
            )
            logger.info("proceso=risk_score status=OK")
            print("Risk score asignado a cotizaciones.")

    dur_total = (time.perf_counter() - t0) * 1000
    logger.info(
        f"proceso=ejecutar_validaciones "
        f"duracion_ms={dur_total:.1f} status=OK"
    )
    return almacen_datos
