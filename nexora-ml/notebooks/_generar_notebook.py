"""
Generador del notebook narrativo 4-Entrenamiento_modelo_IA.ipynb
================================================================
Construye un notebook reproducible que recorre el flujo completo del modelo de
IA de NEXORA reutilizando los módulos de src/. Ejecutar:

    python notebooks/_generar_notebook.py

Esto evita escribir el JSON del .ipynb a mano y mantiene el notebook sincronizado
con la lógica de los módulos.
"""
from pathlib import Path

import nbformat as nbf

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "notebooks" / "4-Entrenamiento_modelo_IA.ipynb"

nb = nbf.v4.new_notebook()
celdas = []


def md(texto: str):
    celdas.append(nbf.v4.new_markdown_cell(texto.strip()))


def code(texto: str):
    celdas.append(nbf.v4.new_code_cell(texto.strip()))


md("""
# 🤖 NEXORA · Entrenamiento del Modelo de IA — Predicción de Abandono (Churn)
### Parcial 3 — ITY1101 Gestión de Datos para IA · DUOC UC
**Equipo:** Esteban Gamboa · Julio Llauri · Joel Sangster

Este notebook recorre el flujo supervisado completo para predecir el **abandono
de suscriptores** de NEXORA, reutilizando los módulos productivos de `src/`:
`preprocesamiento`, `visualizaciones` y `entrenamiento`.

**Flujo:** calidad de datos → análisis univariado/bivariado → preprocesamiento →
entrenamiento de varios algoritmos → ajuste de hiperparámetros → métricas
(matriz de confusión, ROC, **Gini**) → persistencia del modelo.
""")

code("""
import sys
from pathlib import Path

# Permite importar los módulos de src/ desde el notebook
RAIZ = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(RAIZ / "src"))

import preprocesamiento as prep
import visualizaciones as viz
import entrenamiento as ent

print("Módulos cargados desde:", RAIZ / "src")
""")

md("## 📂 Paso 1 — Carga y calidad de datos")
code("""
df = prep.cargar_datos()
calidad = prep.analisis_calidad(df)
print(f"Filas: {calidad['n_filas']} | Columnas: {calidad['n_columnas']}")
print(f"Nulos: {calidad['total_nulos']} | Duplicados: {calidad['duplicados']}")
print(f"Balance objetivo (%): {calidad['balance_objetivo_pct']}")
print(f"Ratio de desbalance: {calidad['ratio_desbalance']} : 1")
df.head()
""")

code("""
# Estadística descriptiva: media, mediana, percentiles
calidad['descriptivas']
""")

md("""
## 🔍 Paso 2 — Análisis exploratorio (univariado, bivariado, correlación)
Generamos las figuras y las mostramos en línea.
""")
code("""
from IPython.display import Image, display

viz.grafico_balance_objetivo(df)
viz.grafico_univariado(df)
viz.grafico_bivariado(df)
viz.grafico_correlacion(df)

for n in ["01_balance_objetivo", "02_univariado", "03_bivariado", "04_correlacion"]:
    display(Image(filename=str(viz.DIR_FIG / f"{n}.png")))
""")

md("""
**Lectura:** el dataset está desbalanceado (~75/25). En el bivariado, los clientes
que abandonan muestran más reclamos y menor antigüedad. No hay multicolinealidad
severa en la matriz de correlación.
""")

md("## ✂️ Paso 3 — Partición estratificada y escalado")
code("""
datos = prep.preparar_datos(df, random_state=42)
print(f"Train: {len(datos['X_train'])} | Test: {len(datos['X_test'])} (80/20 estratificado)")
print("Variables:", datos['columnas'])
""")

md("""
## 🏋️ Paso 4 — Entrenamiento, ajuste y evaluación
Ejecutamos el pipeline de entrenamiento completo (`entrenamiento.main()`), que
entrena 4 algoritmos, optimiza Random Forest con `GridSearchCV`, calcula todas las
métricas, genera las figuras de evaluación y persiste el mejor modelo.
""")
code("""
resumen = ent.main()
print("Modelo seleccionado:", resumen['modelo_seleccionado'])
""")

code("""
import pandas as pd
tabla = pd.DataFrame(resumen['metricas_por_modelo']).T[
    ['accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'gini']
]
tabla
""")

md("## 📏 Paso 5 — Matriz de confusión, Curva ROC y métricas")
code("""
for n in ["05_matriz_confusion", "06_curva_roc", "07_comparacion_metricas", "08_importancia_variables"]:
    display(Image(filename=str(viz.DIR_FIG / f"{n}.png")))
""")

md("""
## 💡 Paso 6 — Interpretación y conclusiones

| Métrica | Valor | Lectura |
|---|---|---|
| Recall | 0,76 | Detecta el 76 % de los abandonos reales (prioridad de negocio). |
| Precision | 0,56 | Cuando alerta, acierta el 56 % (falsas alarmas asumibles). |
| F1 | 0,64 | Equilibrio Precision/Recall. |
| **Gini** | **0,755** | Poder discriminante alto (AUC 0,877). |

**Conclusión:** el manejo del desbalance (`class_weight='balanced'`) y el ajuste de
hiperparámetros elevaron el Recall desde ~48 % (línea base) a **76 %**. El modelo
se prioriza por Recall porque el **falso negativo** (perder un cliente sin
detectarlo) es el error más costoso del negocio. La decisión de retención final la
toma un humano (cumplimiento Ley 21.719).
""")

nb["cells"] = celdas
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
}
nbf.write(nb, DESTINO)
print(f"Notebook generado: {DESTINO}")
