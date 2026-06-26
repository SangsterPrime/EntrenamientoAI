from __future__ import annotations

import time

import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from utils.logger_setup import configurar_logger

logger = configurar_logger(
    "procesamiento.transformacion", archivo="transform.log", consola=False
)


def _normalizar_precios(df: pd.DataFrame) -> pd.DataFrame:
    if "precio_total" not in df.columns:
        return df
    nulos = int(df["precio_total"].isna().sum())
    df["precio_total"] = df["precio_total"].fillna(df["precio_total"].median())
    scaler = MinMaxScaler()
    df["precio_norm"] = scaler.fit_transform(df[["precio_total"]])
    logger.info(
        f"proceso=normalizar_precios metodo=MinMaxScaler "
        f"filas={len(df)} nulos_imputados={nulos} status=OK"
    )
    print("Precios normalizados (0-1).")
    return df


def _categorizar_urgencia(df: pd.DataFrame) -> pd.DataFrame:
    if "urgencia" not in df.columns:
        return df
    mapa = {"alta": "Critico", "media": "Programado", "baja": "No critico"}
    df["urgencia_categoria"] = df["urgencia"].str.lower().map(mapa).fillna("Programado")
    conteo = df["urgencia_categoria"].value_counts().to_dict()
    logger.info(
        f"proceso=categorizar_urgencia categorias=Critico/Programado/No_critico "
        f"distribucion={conteo} status=OK"
    )
    print("Urgencia categorizada.")
    return df


def _calcular_plazo_estandar(df: pd.DataFrame) -> pd.DataFrame:
    if "plazo_dias" not in df.columns:
        return df
    df["plazo_categoria"] = pd.cut(
        df["plazo_dias"],
        bins=[0, 7, 14, 100],
        labels=["Corto (<=7d)", "Medio (8-14d)", "Largo (>14d)"],
    )
    logger.info(f"proceso=calcular_plazo_estandar status=OK")
    print("Plazos de entrega categorizados.")
    return df


def _generar_resumen_cotizaciones(df: pd.DataFrame) -> pd.Series:
    if "proveedor_id" not in df.columns:
        return pd.Series(dtype=int)
    resumen = df.groupby("proveedor_nombre").size()
    logger.info(f"proceso=resumen_cotizaciones status=OK")
    print("Resumen de cotizaciones por proveedor generado.")
    return resumen


def _enriquecer_solicitudes(df_solicitudes: pd.DataFrame, df_cotizaciones: pd.DataFrame) -> pd.DataFrame:
    if df_solicitudes.empty or df_cotizaciones.empty:
        return df_solicitudes
    mejor_precio = df_cotizaciones.loc[df_cotizaciones.groupby("producto")["precio_total"].idxmin()]
    cols = ["producto", "proveedor_nombre", "precio_total"]
    df_mejor = mejor_precio[cols].rename(
        columns={"proveedor_nombre": "mejor_proveedor", "precio_total": "mejor_precio"}
    )
    df_solicitudes = df_solicitudes.merge(df_mejor, on="producto", how="left")
    if "mejor_precio" in df_solicitudes.columns and "presupuesto_max" in df_solicitudes.columns:
        df_solicitudes["ahorro_pct"] = round(
            (df_solicitudes["presupuesto_max"] - df_solicitudes["mejor_precio"])
            / df_solicitudes["presupuesto_max"] * 100, 2
        )
    return df_solicitudes


def generar_transformaciones(almacen_datos: dict) -> dict:
    t0 = time.perf_counter()
    print("\n--- Ejecutando transformaciones NegocIA ---")

    if "Solicitudes" in almacen_datos:
        df = almacen_datos["Solicitudes"].copy()
        df = _categorizar_urgencia(df)
        almacen_datos["Solicitudes"] = df

    if "Cotizaciones" in almacen_datos:
        df_cot = almacen_datos["Cotizaciones"].copy()
        df_cot = _normalizar_precios(df_cot)
        df_cot = _calcular_plazo_estandar(df_cot)
        almacen_datos["Cotizaciones"] = df_cot
        almacen_datos["Resumen_Cotizaciones"] = _generar_resumen_cotizaciones(df_cot)

    if "Solicitudes" in almacen_datos and "Cotizaciones" in almacen_datos:
        almacen_datos["Solicitudes"] = _enriquecer_solicitudes(
            almacen_datos["Solicitudes"], almacen_datos["Cotizaciones"]
        )

    dur_total = (time.perf_counter() - t0) * 1000
    logger.info(
        f"proceso=generar_transformaciones "
        f"duracion_ms={dur_total:.1f} status=OK"
    )
    return almacen_datos
