# NEXORA · Módulo de Inteligencia Predictiva (Churn)

**Parcial 3 — ITY1101 Gestión de Datos para IA · DUOC UC**
Equipo: Esteban Gamboa · Julio Llauri · Joel Sangster

Extensión del pipeline DataOps del proyecto **NEXORA** ("Autonomous Procurement
Intelligence") con un modelo de IA supervisado que predice el **abandono (churn)**
de suscriptores PYME, permitiendo accionar campañas de retención.

---

## 📂 Estructura

```
nexora-ml/
├── data/                  # dataset + salida scoreada
│   └── dataset_churn_telecomunicaciones.csv
├── src/
│   ├── preprocesamiento.py    # calidad de datos, partición, escalado
│   ├── visualizaciones.py     # figuras EDA + evaluación
│   ├── entrenamiento.py       # entrena, evalúa y persiste el modelo
│   └── integracion_pipeline.py# etapa de scoring acoplada al pipeline DataOps
├── notebooks/
│   └── 4-Entrenamiento_modelo_IA.ipynb
├── dashboard/
│   └── app.py             # dashboard BI interactivo (Streamlit)
├── models/                # modelo entrenado (.pkl)
├── reports/               # métricas (JSON/CSV) + figuras (PNG)
└── logs/                  # evidencia de ejecución (rendimiento)
```

## 🚀 Uso

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Entrenar el modelo (genera métricas, figuras y modelo_churn.pkl)
python src/entrenamiento.py

# 3. Ejecutar la etapa de scoring sobre la cartera de clientes
python src/integracion_pipeline.py

# 4. Levantar el dashboard interactivo
streamlit run dashboard/app.py
```

## 📊 Resultados (modelo seleccionado: Random Forest optimizado)

| Métrica   | Valor |
|-----------|-------|
| Accuracy  | 0.79  |
| Recall    | 0.76  |
| Precision | 0.56  |
| F1-Score  | 0.64  |
| ROC-AUC   | 0.877 |
| **Gini**  | **0.755** |

Se priorizó **Recall**: en churn, no detectar un cliente que se va (falso
negativo) es más costoso que una falsa alarma. El manejo del desbalance
(`class_weight='balanced'`) + ajuste de hiperparámetros elevó el Recall desde
~48% (línea base del demo) a **76%**.

## 🔐 Seguridad y datos

Ver `../docs-entrega/seguridad/AUDITORIA_SEGURIDAD.md`. El campo `edad` se trata
como dato personal; el pipeline incluye utilidades de anonimización y la
operación se rige por la Ley 19.628 y la Ley 21.719 (Chile).
