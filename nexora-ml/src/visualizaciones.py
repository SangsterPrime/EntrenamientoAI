"""
NEXORA · Módulo de Inteligencia Predictiva
==========================================
visualizaciones.py — Generación de gráficos de EDA y evaluación.

Centraliza la creación de todas las figuras usadas en el informe técnico y el
dashboard: análisis univariado, bivariado, matriz de correlación, matriz de
confusión, curva ROC, comparación de métricas e importancia de variables.

Todas las figuras se guardan en reports/figures/ en alta resolución (PNG 150 dpi).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend sin ventana, apto para ejecución en nube/CI
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import auc, confusion_matrix, roc_curve

# --- Identidad visual NEXORA -------------------------------------------------
AZUL = "#1F4E79"
AZUL_CLARO = "#2E86C1"
ROJO = "#C0392B"
NARANJA = "#E67E22"
VERDE = "#27AE60"
MORADO = "#8E44AD"
GRIS = "#7F8C8D"
PALETA = [AZUL, ROJO, VERDE, NARANJA, MORADO, AZUL_CLARO]

RAIZ = Path(__file__).resolve().parents[1]
DIR_FIG = RAIZ / "reports" / "figures"
DIR_FIG.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid")
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 150, "font.size": 10})


def _guardar(fig, nombre: str) -> Path:
    ruta = DIR_FIG / nombre
    fig.tight_layout()
    fig.savefig(ruta, bbox_inches="tight")
    plt.close(fig)
    return ruta


def grafico_balance_objetivo(df: pd.DataFrame, objetivo: str = "abandona") -> Path:
    """Distribución de la variable objetivo (barras + torta)."""
    conteo = df[objetivo].value_counts().sort_index()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(["No abandona (0)", "Sí abandona (1)"], conteo.values,
                color=[AZUL, ROJO], edgecolor="white", linewidth=1.5)
    axes[0].set_title("Distribución de Abandono (Churn)", fontweight="bold")
    axes[0].set_ylabel("N° de clientes")
    for i, v in enumerate(conteo.values):
        axes[0].text(i, v + 3, str(v), ha="center", fontweight="bold")
    axes[1].pie(conteo.values, labels=["No abandona", "Sí abandona"], autopct="%1.1f%%",
                colors=[AZUL, ROJO], startangle=90, textprops={"color": "black"})
    axes[1].set_title("Proporción de clases", fontweight="bold")
    return _guardar(fig, "01_balance_objetivo.png")


def grafico_univariado(df: pd.DataFrame, objetivo: str = "abandona") -> Path:
    """Histogramas de cada variable predictora (análisis univariado)."""
    predictoras = [c for c in df.columns if c != objetivo]
    n = len(predictoras)
    filas = int(np.ceil(n / 3))
    fig, axes = plt.subplots(filas, 3, figsize=(14, 3.4 * filas))
    axes = np.array(axes).ravel()
    for i, col in enumerate(predictoras):
        axes[i].hist(df[col], bins=20, color=AZUL_CLARO, edgecolor="white")
        axes[i].axvline(df[col].mean(), color=ROJO, linestyle="--", linewidth=1.5,
                        label=f"media={df[col].mean():.1f}")
        axes[i].set_title(f"Distribución · {col}", fontweight="bold")
        axes[i].legend(fontsize=8)
    for j in range(n, len(axes)):
        axes[j].axis("off")
    fig.suptitle("Análisis Univariado de Variables Predictoras", fontsize=14, fontweight="bold")
    return _guardar(fig, "02_univariado.png")


def grafico_bivariado(df: pd.DataFrame, objetivo: str = "abandona") -> Path:
    """Boxplots de cada variable según la clase objetivo (análisis bivariado)."""
    predictoras = [c for c in df.columns if c != objetivo]
    n = len(predictoras)
    filas = int(np.ceil(n / 3))
    fig, axes = plt.subplots(filas, 3, figsize=(14, 3.4 * filas))
    axes = np.array(axes).ravel()
    for i, col in enumerate(predictoras):
        datos = [df[df[objetivo] == 0][col], df[df[objetivo] == 1][col]]
        bp = axes[i].boxplot(datos, tick_labels=["No\nabandona", "Sí\nabandona"], patch_artist=True)
        for parche, color in zip(bp["boxes"], [AZUL, ROJO]):
            parche.set_facecolor(color)
            parche.set_alpha(0.7)
        axes[i].set_title(f"{col} vs abandono", fontweight="bold")
    for j in range(n, len(axes)):
        axes[j].axis("off")
    fig.suptitle("Análisis Bivariado · Variable vs. Abandono", fontsize=14, fontweight="bold")
    return _guardar(fig, "03_bivariado.png")


def grafico_correlacion(df: pd.DataFrame) -> Path:
    """Matriz de correlación de Pearson."""
    corr = df.corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(8, 6.5))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                square=True, linewidths=0.5, cbar_kws={"shrink": 0.8}, ax=ax)
    ax.set_title("Matriz de Correlación", fontweight="bold")
    return _guardar(fig, "04_correlacion.png")


def grafico_matriz_confusion(y_true, y_pred, nombre_modelo: str) -> Path:
    """Matriz de confusión con etiquetas TN/FP/FN/TP."""
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.set_title(f"Matriz de Confusión · {nombre_modelo}", fontweight="bold")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["Pred: No", "Pred: Sí"])
    ax.set_yticklabels(["Real: No", "Real: Sí"])
    ax.set_xlabel("Predicción"); ax.set_ylabel("Valor real")
    etiquetas = [["TN", "FP"], ["FN", "TP"]]
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]}\n({etiquetas[i][j]})", ha="center", va="center",
                    fontsize=14, fontweight="bold",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    return _guardar(fig, "05_matriz_confusion.png")


def grafico_curva_roc(resultados: dict, y_test) -> Path:
    """Curva ROC comparada de todos los modelos, con AUC y Gini."""
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    for i, (nombre, r) in enumerate(resultados.items()):
        if r.get("y_proba") is None:
            continue
        fpr, tpr, _ = roc_curve(y_test, r["y_proba"])
        a = auc(fpr, tpr)
        gini = 2 * a - 1
        ax.plot(fpr, tpr, color=PALETA[i % len(PALETA)], linewidth=2,
                label=f"{nombre} (AUC={a:.3f}, Gini={gini:.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Azar (AUC=0.5)")
    ax.set_xlabel("Tasa de Falsos Positivos (1 - Especificidad)")
    ax.set_ylabel("Tasa de Verdaderos Positivos (Recall)")
    ax.set_title("Curva ROC — Comparación de Modelos", fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    return _guardar(fig, "06_curva_roc.png")


def grafico_comparacion_metricas(resultados: dict) -> Path:
    """Barras agrupadas comparando métricas clave entre modelos."""
    metricas = ["accuracy", "precision", "recall", "f1", "gini"]
    modelos = list(resultados.keys())
    x = np.arange(len(metricas))
    ancho = 0.8 / len(modelos)
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for i, m in enumerate(modelos):
        valores = [resultados[m][k] for k in metricas]
        barras = ax.bar(x + i * ancho, valores, ancho, label=m,
                        color=PALETA[i % len(PALETA)], edgecolor="white")
        for b, v in zip(barras, valores):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.2f}",
                    ha="center", fontsize=7.5, fontweight="bold")
    ax.set_xticks(x + ancho * (len(modelos) - 1) / 2)
    ax.set_xticklabels([m.upper() for m in metricas])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Puntaje")
    ax.set_title("Comparación de Métricas por Modelo", fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)
    return _guardar(fig, "07_comparacion_metricas.png")


def grafico_importancia(importancias: pd.Series, nombre_modelo: str) -> Path:
    """Importancia de variables (feature importance / coeficientes)."""
    importancias = importancias.sort_values()
    fig, ax = plt.subplots(figsize=(8, 5))
    colores = [ROJO if v < 0 else AZUL for v in importancias.values]
    ax.barh(importancias.index, importancias.values, color=colores, edgecolor="white")
    ax.set_title(f"Importancia de Variables · {nombre_modelo}", fontweight="bold")
    ax.set_xlabel("Peso relativo")
    return _guardar(fig, "08_importancia_variables.png")
