"""
NEXORA · Módulo de Inteligencia Predictiva
==========================================
preprocesamiento.py — Calidad de datos, partición y escalado.

Este módulo concentra la fase previa al entrenamiento del modelo de IA que
predice el abandono (churn) de suscriptores PYME de la plataforma NEXORA:

    1. Carga del dataset.
    2. Análisis de calidad de datos (nulos, duplicados, estadística descriptiva).
    3. Partición estratificada train/test.
    4. Escalado de variables numéricas.

Se diseñó como módulo importable para integrarse al pipeline DataOps del
Parcial 2 (etapa de procesamiento) y, a la vez, ejecutable de forma aislada.

Autores: Esteban Gamboa · Julio Llauri · Joel Sangster
Asignatura: ITY1101 — Gestión de Datos para IA · DUOC UC
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# --- Rutas base del proyecto -------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
RUTA_DATASET = RAIZ / "data" / "dataset_churn_telecomunicaciones.csv"

# Variable objetivo del problema de clasificación binaria
OBJETIVO = "abandona"

# Diccionario de datos: descripción y clasificación de sensibilidad.
# Se usa también en la auditoría de seguridad (datos personales vs. operativos).
DICCIONARIO_DATOS = {
    "edad": {"desc": "Edad del titular de la cuenta (años)", "tipo": "numerica", "sensible": True},
    "anos_cliente": {"desc": "Antigüedad como suscriptor NEXORA (años)", "tipo": "numerica", "sensible": False},
    "uso_datos_gb": {"desc": "Uso mensual de la plataforma (GB equivalente)", "tipo": "numerica", "sensible": False},
    "llamadas_mes": {"desc": "Interacciones con soporte / API al mes", "tipo": "numerica", "sensible": False},
    "reclamos": {"desc": "N° de reclamos en el último año", "tipo": "numerica", "sensible": False},
    "plan_premium": {"desc": "Suscriptor de plan premium (1=Sí, 0=No)", "tipo": "categorica", "sensible": False},
    "abandona": {"desc": "Cliente abandonó la plataforma (1=Sí, 0=No) — OBJETIVO", "tipo": "binaria", "sensible": False},
}


def cargar_datos(ruta: str | Path = RUTA_DATASET) -> pd.DataFrame:
    """Carga el dataset de churn desde un CSV y devuelve un DataFrame."""
    df = pd.read_csv(ruta)
    return df


def analisis_calidad(df: pd.DataFrame) -> dict:
    """
    Ejecuta un análisis de calidad de datos y devuelve un diccionario con las
    métricas exigidas por la rúbrica: media, mediana, percentiles, nulos,
    duplicados y balance de la variable objetivo.
    """
    desc = df.describe().T
    desc["mediana"] = df.median(numeric_only=True)
    # Percentiles 25/50/75 ya vienen en describe(); agregamos moda por columna.
    modas = {c: df[c].mode().iloc[0] if not df[c].mode().empty else np.nan for c in df.columns}

    conteo_obj = df[OBJETIVO].value_counts().sort_index()
    balance = (df[OBJETIVO].value_counts(normalize=True) * 100).sort_index().round(2)

    reporte = {
        "n_filas": int(df.shape[0]),
        "n_columnas": int(df.shape[1]),
        "columnas": list(df.columns),
        "tipos": df.dtypes.astype(str).to_dict(),
        "nulos_por_columna": df.isnull().sum().to_dict(),
        "total_nulos": int(df.isnull().sum().sum()),
        "duplicados": int(df.duplicated().sum()),
        "modas": modas,
        "descriptivas": desc.round(3),
        "balance_objetivo_conteo": conteo_obj.to_dict(),
        "balance_objetivo_pct": balance.to_dict(),
        "ratio_desbalance": round(conteo_obj.max() / conteo_obj.min(), 2),
    }
    return reporte


def imputar_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Imputación básica: mediana para numéricas, moda para categóricas.
    El dataset entregado no presenta nulos, pero se deja la función como
    salvaguarda de robustez del pipeline ante datos reales.
    """
    df = df.copy()
    for col in df.columns:
        if df[col].isnull().any():
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].median())
            else:
                df[col] = df[col].fillna(df[col].mode().iloc[0])
    return df


def preparar_datos(
    df: pd.DataFrame,
    objetivo: str = OBJETIVO,
    test_size: float = 0.2,
    random_state: int = 42,
    escalar: bool = True,
):
    """
    Separa X/y, hace partición estratificada y escala las variables numéricas.

    Devuelve un diccionario con los conjuntos escalados y sin escalar
    (los modelos de árbol no requieren escalado; la regresión logística sí).
    """
    df = imputar_nulos(df)
    X = df.drop(columns=[objetivo])
    y = df[objetivo]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    scaler = StandardScaler()
    X_train_esc = pd.DataFrame(
        scaler.fit_transform(X_train), columns=X.columns, index=X_train.index
    )
    X_test_esc = pd.DataFrame(
        scaler.transform(X_test), columns=X.columns, index=X_test.index
    )

    return {
        "X": X,
        "y": y,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "X_train_esc": X_train_esc if escalar else X_train,
        "X_test_esc": X_test_esc if escalar else X_test,
        "scaler": scaler,
        "columnas": list(X.columns),
    }


if __name__ == "__main__":
    datos = cargar_datos()
    rep = analisis_calidad(datos)
    print(f"Filas: {rep['n_filas']} | Columnas: {rep['n_columnas']}")
    print(f"Nulos totales: {rep['total_nulos']} | Duplicados: {rep['duplicados']}")
    print(f"Balance objetivo (%): {rep['balance_objetivo_pct']}")
    print(f"Ratio de desbalance: {rep['ratio_desbalance']} : 1")
    print("\nEstadística descriptiva:")
    print(rep["descriptivas"])
