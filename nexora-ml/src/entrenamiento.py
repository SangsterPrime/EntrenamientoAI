"""
NEXORA · Módulo de Inteligencia Predictiva
==========================================
entrenamiento.py — Entrenamiento, comparación y evaluación del modelo de IA.

Flujo completo de un modelo supervisado de clasificación binaria para predecir
el abandono (churn) de suscriptores de NEXORA:

    1. Calidad de datos y partición estratificada (preprocesamiento.py).
    2. Análisis exploratorio (univariado, bivariado, correlación).
    3. Entrenamiento de 4 algoritmos con manejo del desbalance de clases.
    4. Ajuste de hiperparámetros (GridSearchCV) sobre el mejor candidato.
    5. Evaluación: accuracy, precision, recall, F1, ROC-AUC y coeficiente de Gini.
    6. Persistencia del modelo (joblib), métricas (JSON) y figuras (PNG).
    7. Logging de rendimiento para evidencia de operación en nube/local.

Ejecución:  python src/entrenamiento.py
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV
from sklearn.tree import DecisionTreeClassifier

import preprocesamiento as prep
import visualizaciones as viz

# --- Rutas y configuración ---------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
DIR_MODELOS = RAIZ / "models"
DIR_REPORTS = RAIZ / "reports"
DIR_LOGS = RAIZ / "logs"
for d in (DIR_MODELOS, DIR_REPORTS, DIR_LOGS):
    d.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42

# --- Logging (archivo + consola) --------------------------------------------
logger = logging.getLogger("nexora.entrenamiento")
logger.setLevel(logging.INFO)
logger.handlers.clear()
_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
_fh = logging.FileHandler(DIR_LOGS / "entrenamiento.log", encoding="utf-8")
_fh.setFormatter(_fmt)
_ch = logging.StreamHandler()
_ch.setFormatter(_fmt)
logger.addHandler(_fh)
logger.addHandler(_ch)


def construir_modelos() -> dict:
    """Define los algoritmos candidatos. Todos manejan el desbalance de clases."""
    return {
        "Regresión Logística": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Árbol de Decisión": DecisionTreeClassifier(
            max_depth=5, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=6, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=150, max_depth=3, random_state=RANDOM_STATE
        ),
    }


def evaluar(modelo, X_test, y_test) -> dict:
    """Calcula todas las métricas exigidas por la rúbrica para un modelo."""
    y_pred = modelo.predict(X_test)
    y_proba = modelo.predict_proba(X_test)[:, 1] if hasattr(modelo, "predict_proba") else None

    auc_val = roc_auc_score(y_test, y_proba) if y_proba is not None else np.nan
    return {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc": round(auc_val, 4),
        "gini": round(2 * auc_val - 1, 4),  # Gini = 2 * AUC - 1
        "y_pred": y_pred,
        "y_proba": y_proba,
    }


def importancia_variables(modelo, columnas) -> pd.Series:
    """Extrae importancia de variables (árboles) o coeficientes (lineal)."""
    if hasattr(modelo, "feature_importances_"):
        return pd.Series(modelo.feature_importances_, index=columnas)
    if hasattr(modelo, "coef_"):
        return pd.Series(modelo.coef_[0], index=columnas)
    return pd.Series(dtype=float)


def ajustar_hiperparametros(X_train, y_train) -> tuple:
    """GridSearchCV sobre Random Forest optimizando Recall (clave en churn)."""
    logger.info("Iniciando ajuste de hiperparámetros (GridSearchCV) sobre Random Forest")
    grid = {
        "n_estimators": [100, 200, 300],
        "max_depth": [4, 6, 8, None],
        "min_samples_leaf": [1, 2, 4],
    }
    base = RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE)
    # n_jobs=1: evita el ruido de limpieza de loky en Windows durante la demo.
    # El dataset es pequeño, por lo que el costo en tiempo es despreciable.
    busqueda = GridSearchCV(base, grid, scoring="recall", cv=5, n_jobs=1)
    busqueda.fit(X_train, y_train)
    logger.info(f"Mejores hiperparámetros: {busqueda.best_params_}")
    logger.info(f"Mejor Recall (CV=5): {busqueda.best_score_:.4f}")
    return busqueda.best_estimator_, busqueda.best_params_, round(busqueda.best_score_, 4)


def main() -> dict:
    t0 = time.perf_counter()
    logger.info("=" * 70)
    logger.info("NEXORA · Inicio del entrenamiento del modelo de IA (churn)")

    # 1. Carga y calidad de datos --------------------------------------------
    df = prep.cargar_datos()
    calidad = prep.analisis_calidad(df)
    logger.info(f"Dataset cargado: {calidad['n_filas']} filas x {calidad['n_columnas']} columnas")
    logger.info(f"Nulos: {calidad['total_nulos']} | Duplicados: {calidad['duplicados']}")
    logger.info(f"Balance objetivo (%): {calidad['balance_objetivo_pct']} "
                f"| Ratio desbalance: {calidad['ratio_desbalance']}:1")

    # 2. Análisis exploratorio (figuras) -------------------------------------
    logger.info("Generando figuras de análisis exploratorio (EDA)")
    viz.grafico_balance_objetivo(df)
    viz.grafico_univariado(df)
    viz.grafico_bivariado(df)
    viz.grafico_correlacion(df)

    # 3. Partición y escalado -------------------------------------------------
    datos = prep.preparar_datos(df, random_state=RANDOM_STATE)
    logger.info(f"Partición: train={len(datos['X_train'])} | test={len(datos['X_test'])} (80/20 estratificado)")

    # 4. Entrenamiento de modelos candidatos ----------------------------------
    # Los modelos lineales usan datos escalados; los de árbol, datos crudos.
    modelos = construir_modelos()
    resultados = {}
    objetos_modelo = {}
    for nombre, modelo in modelos.items():
        usar_escalado = isinstance(modelo, LogisticRegression)
        Xtr = datos["X_train_esc"] if usar_escalado else datos["X_train"]
        Xte = datos["X_test_esc"] if usar_escalado else datos["X_test"]
        t_ini = time.perf_counter()
        modelo.fit(Xtr, datos["y_train"])
        dur = time.perf_counter() - t_ini
        met = evaluar(modelo, Xte, datos["y_test"])
        met["tiempo_entrenamiento_s"] = round(dur, 4)
        met["escalado"] = usar_escalado
        resultados[nombre] = met
        objetos_modelo[nombre] = modelo
        logger.info(
            f"[{nombre}] acc={met['accuracy']} prec={met['precision']} "
            f"recall={met['recall']} f1={met['f1']} auc={met['roc_auc']} "
            f"gini={met['gini']} ({dur:.3f}s)"
        )

    # 5. Ajuste de hiperparámetros del mejor candidato ------------------------
    rf_opt, mejores_params, mejor_cv = ajustar_hiperparametros(datos["X_train"], datos["y_train"])
    met_opt = evaluar(rf_opt, datos["X_test"], datos["y_test"])
    met_opt["tiempo_entrenamiento_s"] = None
    met_opt["escalado"] = False
    resultados["Random Forest (optimizado)"] = met_opt
    objetos_modelo["Random Forest (optimizado)"] = rf_opt
    logger.info(
        f"[Random Forest (optimizado)] acc={met_opt['accuracy']} prec={met_opt['precision']} "
        f"recall={met_opt['recall']} f1={met_opt['f1']} auc={met_opt['roc_auc']} gini={met_opt['gini']}"
    )

    # 6. Selección del mejor modelo (prioriza Recall, desempata por F1) -------
    mejor_nombre = max(resultados, key=lambda n: (resultados[n]["recall"], resultados[n]["f1"]))
    mejor_modelo = objetos_modelo[mejor_nombre]
    logger.info(f"MODELO SELECCIONADO: {mejor_nombre} "
                f"(Recall={resultados[mejor_nombre]['recall']}, F1={resultados[mejor_nombre]['f1']})")

    # 7. Figuras de evaluación del mejor modelo ------------------------------
    viz.grafico_matriz_confusion(datos["y_test"], resultados[mejor_nombre]["y_pred"], mejor_nombre)
    viz.grafico_curva_roc(resultados, datos["y_test"])
    viz.grafico_comparacion_metricas(resultados)
    imp = importancia_variables(mejor_modelo, datos["columnas"])
    if not imp.empty:
        viz.grafico_importancia(imp, mejor_nombre)

    # 8. Persistencia ---------------------------------------------------------
    paquete = {
        "modelo": mejor_modelo,
        "scaler": datos["scaler"],
        "columnas": datos["columnas"],
        "nombre_modelo": mejor_nombre,
        "requiere_escalado": isinstance(mejor_modelo, LogisticRegression),
    }
    ruta_modelo = DIR_MODELOS / "modelo_churn.pkl"
    joblib.dump(paquete, ruta_modelo)
    logger.info(f"Modelo persistido en {ruta_modelo}")

    # Métricas a JSON (sin arrays de predicción)
    metricas_export = {
        n: {k: v for k, v in r.items() if k not in ("y_pred", "y_proba")}
        for n, r in resultados.items()
    }
    salida = {
        "modelo_seleccionado": mejor_nombre,
        "criterio_seleccion": "Máximo Recall (coste de falso negativo alto), desempate por F1",
        "hiperparametros_optimizados": mejores_params,
        "recall_cv5_optimizado": mejor_cv,
        "matriz_confusion": confusion_matrix(
            datos["y_test"], resultados[mejor_nombre]["y_pred"]
        ).tolist(),
        "calidad_datos": {
            "n_filas": calidad["n_filas"],
            "n_columnas": calidad["n_columnas"],
            "nulos": calidad["total_nulos"],
            "duplicados": calidad["duplicados"],
            "balance_pct": calidad["balance_objetivo_pct"],
            "ratio_desbalance": calidad["ratio_desbalance"],
        },
        "metricas_por_modelo": metricas_export,
        "importancia_variables": imp.round(4).to_dict() if not imp.empty else {},
        "tiempo_total_s": round(time.perf_counter() - t0, 3),
    }
    ruta_metricas = DIR_REPORTS / "metricas.json"
    ruta_metricas.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Métricas exportadas a {ruta_metricas}")

    # Tabla comparativa CSV (útil para el dashboard y el informe)
    tabla = pd.DataFrame(metricas_export).T[
        ["accuracy", "precision", "recall", "f1", "roc_auc", "gini"]
    ]
    tabla.to_csv(DIR_REPORTS / "comparacion_modelos.csv", encoding="utf-8")

    # Reporte de clasificación del mejor modelo
    rep_txt = classification_report(
        datos["y_test"], resultados[mejor_nombre]["y_pred"],
        target_names=["No abandona", "Sí abandona"],
    )
    logger.info("Reporte de clasificación del modelo seleccionado:\n" + rep_txt)
    logger.info(f"Entrenamiento finalizado en {salida['tiempo_total_s']}s")
    logger.info("=" * 70)

    return salida


if __name__ == "__main__":
    resumen = main()
    print("\n" + "=" * 60)
    print(f"  Modelo seleccionado : {resumen['modelo_seleccionado']}")
    print(f"  Tiempo total        : {resumen['tiempo_total_s']} s")
    print("  Métricas:")
    for nombre, m in resumen["metricas_por_modelo"].items():
        print(f"    - {nombre:<28} recall={m['recall']:.3f}  f1={m['f1']:.3f}  gini={m['gini']:.3f}")
    print("=" * 60)
