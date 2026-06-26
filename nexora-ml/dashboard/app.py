"""
NEXORA · Dashboard de Inteligencia Predictiva (BI)
==================================================
app.py — Panel interactivo en Streamlit con los resultados del modelo de IA
que predice el abandono (churn) de suscriptores de NEXORA.

Secciones:
    1. KPIs del modelo seleccionado (accuracy, recall, F1, Gini, AUC).
    2. Comparación visual de modelos (tabla + figuras de evaluación).
    3. Análisis exploratorio (EDA) del dataset.
    4. Predictor en vivo: estima la probabilidad de abandono de un cliente.
    5. Rendimiento operativo (logs de entrenamiento).

Ejecución:  streamlit run dashboard/app.py
Despliegue: compatible con Streamlit Community Cloud (entorno nube).
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

# --- Rutas ------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
DIR_REPORTS = RAIZ / "reports"
DIR_FIG = DIR_REPORTS / "figures"
DIR_MODELOS = RAIZ / "models"
DIR_LOGS = RAIZ / "logs"
RUTA_DATASET = RAIZ / "data" / "dataset_churn_telecomunicaciones.csv"

AZUL = "#1F4E79"

st.set_page_config(page_title="NEXORA · Inteligencia Predictiva",
                   page_icon="📊", layout="wide")


# --- Carga de recursos (cacheada) -------------------------------------------
@st.cache_data
def cargar_metricas() -> dict:
    ruta = DIR_REPORTS / "metricas.json"
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def cargar_dataset() -> pd.DataFrame:
    return pd.read_csv(RUTA_DATASET)


@st.cache_resource
def cargar_modelo():
    # Seguridad: modelo_churn.pkl es un artefacto producido localmente por
    # src/entrenamiento.py (fuente confiable del propio proyecto), no un
    # archivo externo. joblib es el mecanismo estándar de persistencia de
    # scikit-learn. No se cargan pickles de origen no confiable.
    ruta = DIR_MODELOS / "modelo_churn.pkl"
    return joblib.load(ruta) if ruta.exists() else None


metricas = cargar_metricas()
df = cargar_dataset()
paquete = cargar_modelo()

# --- Encabezado --------------------------------------------------------------
st.markdown(
    f"<h1 style='color:{AZUL};margin-bottom:0'>NEXORA · Inteligencia Predictiva</h1>"
    "<p style='color:#7F8C8D;margin-top:4px'>Predicción de abandono (churn) de "
    "suscriptores PYME · ITY1101 Gestión de Datos para IA · DUOC UC</p>",
    unsafe_allow_html=True,
)

if not metricas:
    st.warning("No se encontró reports/metricas.json. Ejecuta primero "
               "`python src/entrenamiento.py`.")
    st.stop()

seleccionado = metricas["modelo_seleccionado"]
met_sel = metricas["metricas_por_modelo"][seleccionado]

# --- Barra lateral -----------------------------------------------------------
with st.sidebar:
    st.header("ℹ️ Resumen del modelo")
    st.metric("Modelo en producción", seleccionado)
    st.caption(f"Criterio: {metricas['criterio_seleccion']}")
    st.write("**Hiperparámetros óptimos**")
    st.json(metricas["hiperparametros_optimizados"])
    cal = metricas["calidad_datos"]
    st.write("**Calidad de datos**")
    st.write(f"- Registros: {cal['n_filas']}")
    st.write(f"- Nulos: {cal['nulos']} · Duplicados: {cal['duplicados']}")
    st.write(f"- Desbalance: {cal['ratio_desbalance']}:1")

# --- Pestañas ----------------------------------------------------------------
tab_kpi, tab_modelos, tab_eda, tab_pred, tab_logs = st.tabs(
    ["📈 KPIs", "🤖 Modelos", "🔍 Datos (EDA)", "🎯 Predictor en vivo", "📜 Rendimiento"]
)

# 1. KPIs
with tab_kpi:
    st.subheader(f"Indicadores clave · {seleccionado}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Accuracy", f"{met_sel['accuracy']*100:.1f}%")
    c2.metric("Recall", f"{met_sel['recall']*100:.1f}%",
              help="De cada 100 clientes que abandonan, cuántos detecta el modelo")
    c3.metric("Precision", f"{met_sel['precision']*100:.1f}%")
    c4.metric("F1-Score", f"{met_sel['f1']*100:.1f}%")
    c5.metric("Gini", f"{met_sel['gini']:.3f}",
              help="Gini = 2·AUC − 1. Poder discriminante del modelo")
    st.divider()
    colA, colB = st.columns(2)
    with colA:
        st.image(str(DIR_FIG / "05_matriz_confusion.png"),
                 caption="Matriz de confusión del modelo seleccionado")
    with colB:
        st.image(str(DIR_FIG / "06_curva_roc.png"),
                 caption="Curva ROC — comparación de modelos")
    st.info(
        f"**Interpretación de negocio:** el modelo detecta el "
        f"**{met_sel['recall']*100:.0f}%** de los clientes que efectivamente abandonan. "
        "Cada abandono no detectado (falso negativo) implica perder un suscriptor sin "
        "posibilidad de retenerlo, por lo que se priorizó maximizar el Recall."
    )

# 2. Modelos
with tab_modelos:
    st.subheader("Comparación de algoritmos")
    tabla = pd.DataFrame(metricas["metricas_por_modelo"]).T[
        ["accuracy", "precision", "recall", "f1", "roc_auc", "gini"]
    ].astype(float)
    st.dataframe(
        tabla.style.format("{:.3f}").highlight_max(axis=0, color="#D5F5E3"),
        use_container_width=True,
    )
    st.image(str(DIR_FIG / "07_comparacion_metricas.png"), use_container_width=True)
    if (DIR_FIG / "08_importancia_variables.png").exists():
        st.image(str(DIR_FIG / "08_importancia_variables.png"),
                 caption="Variables más influyentes en la predicción de abandono")

# 3. EDA
with tab_eda:
    st.subheader("Análisis exploratorio de datos")
    st.image(str(DIR_FIG / "01_balance_objetivo.png"), use_container_width=True)
    st.image(str(DIR_FIG / "02_univariado.png"), use_container_width=True)
    st.image(str(DIR_FIG / "03_bivariado.png"), use_container_width=True)
    st.image(str(DIR_FIG / "04_correlacion.png"), width=650)
    with st.expander("Ver estadística descriptiva"):
        st.dataframe(df.describe().T.round(2), use_container_width=True)

# 4. Predictor en vivo
with tab_pred:
    st.subheader("Predictor de abandono en vivo")
    if paquete is None:
        st.error("Modelo no disponible. Ejecuta `python src/entrenamiento.py`.")
    else:
        st.caption("Ajusta el perfil del cliente y obtén la probabilidad estimada de abandono.")
        col1, col2, col3 = st.columns(3)
        edad = col1.slider("Edad", 18, 69, 45)
        anos = col1.slider("Años como cliente", 1, 9, 5)
        uso = col2.slider("Uso de datos (GB/mes)", 0.5, 20.0, 10.5, 0.1)
        llamadas = col2.slider("Interacciones soporte/mes", 0, 99, 47)
        reclamos = col3.slider("Reclamos último año", 0, 4, 2)
        premium = col3.selectbox("Plan premium", ["No", "Sí"]) == "Sí"

        entrada = pd.DataFrame([{
            "edad": edad, "anos_cliente": anos, "uso_datos_gb": uso,
            "llamadas_mes": llamadas, "reclamos": reclamos,
            "plan_premium": int(premium),
        }])[paquete["columnas"]]

        modelo = paquete["modelo"]
        X = paquete["scaler"].transform(entrada) if paquete.get("requiere_escalado") else entrada
        proba = float(modelo.predict_proba(X)[0, 1])
        pred = int(proba >= 0.5)

        st.divider()
        m1, m2 = st.columns([1, 2])
        m1.metric("Probabilidad de abandono", f"{proba*100:.1f}%")
        if pred == 1:
            m2.error("⚠️ **Cliente en RIESGO de abandono** — activar acción de retención.")
        else:
            m2.success("✅ **Cliente estable** — sin alerta de abandono.")
        st.progress(proba)

# 5. Rendimiento / logs
with tab_logs:
    st.subheader("Rendimiento operativo (evidencia de ejecución)")
    st.write(f"Tiempo total de entrenamiento: **{metricas.get('tiempo_total_s','—')} s**")
    log = DIR_LOGS / "entrenamiento.log"
    if log.exists():
        contenido = log.read_text(encoding="utf-8").splitlines()
        st.code("\n".join(contenido[-40:]), language="log")
    else:
        st.info("No hay logs disponibles aún.")
