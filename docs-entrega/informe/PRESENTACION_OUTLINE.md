# NEXORA — Guion de Presentación (Defensa Parcial 3)
### 15 min exposición + demo · 5 min preguntas · ITY1101

**Equipo:** Esteban Gamboa · Julio Llauri · Joel Sangster
**Sugerencia de tiempo:** repartir equitativamente; cada integrante domina TODO
(el docente puede preguntar a cualquiera sobre cualquier parte).

> Recurso de apoyo (PPT/Canva): usar las figuras de `reports/figures/`. No leer
> las diapositivas; usarlas como soporte.

---

## Estructura de diapositivas

### Slide 1 — Portada
NEXORA · Inteligencia Predictiva de Abandono (Churn). Integrantes, sección, sigla.

### Slide 2 — Síntesis de Fase 1 (Parcial 2) *(contextualizar)*
- **Caso:** NEXORA, automatización de adquisiciones para PYMEs chilenas.
- **Roles:** Diseño (Julio), Ingesta (Esteban), Transformación (Joel), etc.
- **Metodología:** Híbrida PMBOK (predictiva + adaptativa).
- **Entregables P2:** pipeline DataOps (ingesta→transformación→validación→carga),
  demo n8n, plan de seguridad, KPIs.

### Slide 3 — De gestionar a predecir *(el "porqué" del Parcial 3)*
NEXORA evoluciona a SaaS → problema de negocio: **retención de suscriptores**.
La solución: un modelo de IA que predice el abandono y acciona retención.

### Slide 4 — Análisis de calidad de datos
- 500 registros, 0 nulos, 0 duplicados.
- Estadística: media/mediana/percentiles (tabla descriptiva).
- **Desbalance 74,6 % / 25,4 % (2,94:1)** → decisión clave de modelado.
- *(Figura 1: balance objetivo)*

### Slide 5 — Análisis univariado y bivariado + correlación
- Univariado (Fig. 2): distribución de cada variable.
- Bivariado (Fig. 3): quienes abandonan → más reclamos, menos antigüedad.
- Matriz de correlación (Fig. 4): sin multicolinealidad severa.

### Slide 6 — Entrenamiento y elección del modelo
- 4 algoritmos + Random Forest optimizado (GridSearchCV, prioriza Recall).
- **Justificación:** en churn, el falso negativo (perder un cliente sin detectar)
  es el error más costoso → optimizar **Recall**.

### Slide 7 — Métricas e interpretación
- Tabla comparativa (Accuracy/Precision/Recall/F1/AUC/**Gini**).
- Modelo elegido: **Recall 0,76 · F1 0,64 · Gini 0,755 · AUC 0,877**.
- Matriz de confusión (Fig. 5) + Curva ROC (Fig. 6).
- **Interpretación:** detecta 19/25 abandonos; Gini alto = buen poder discriminante;
  mejora desde ~48 % de la línea base.

### Slide 8 — Seguridad y Ley de Datos
- Clasificación: `edad` = dato personal; `prob_abandono` = perfilamiento.
- Seudonimización + generalización + RBAC (4 roles).
- **Ley 19.628 + Ley 21.719**; derecho a no decisión 100 % automatizada → humano en el circuito.

### Slide 9 — Limitaciones y mejoras
- Limitaciones: dataset pequeño, desbalance, precision moderada, *data drift*.
- Mejoras: SMOTE/threshold, monitoreo de drift, SHAP, API REST, serialización segura.

### Slide 10 — DEMO en vivo
1. `python pipeline.py` → flujo completo (ingesta → transformación → validación → scoring IA → seguridad → carga SQLite → KPIs con alertas).
2. `streamlit run dashboard/app.py` → KPIs, comparación, **predictor en vivo**.
3. **n8n workflow:** mostrar `nexora-ml/n8n_workflows/carga_scoreados.json` importado en n8n, ejecutar y ver los datos en PostgreSQL.

### Slide 11 — Hallazgos, integración BI, n8n y cierre
- Integración: pipeline → scoring → dashboard → n8n (workflow automatizado) → PostgreSQL → acción de retención.
- Workflow n8n exportado en `nexora-ml/n8n_workflows/` con 5 nodos.
- Dockerfile para despliegue cloud (Azure/AWS/GCP).
- 124 clientes en riesgo ALTO detectados.
- Conclusión + próximos pasos.

---

## Banco de preguntas de defensa (preparación individual — vale 70%)

**Sobre métricas (indicador 8, 30%):**
- *¿Por qué Recall y no Accuracy?* → Por el desbalance: un modelo que dice
  "nadie abandona" tendría 75 % de accuracy y sería inútil. El negocio necesita
  detectar a los que se van (Recall).
- *¿Qué es el Gini y cómo se relaciona con la ROC?* → Gini = 2·AUC − 1. Mide el
  poder discriminante; 0 = azar, 1 = perfecto. Nuestro 0,755 = AUC 0,877.
- *¿Qué es un falso negativo aquí y por qué importa?* → Cliente que abandona y el
  modelo no detecta → se pierde sin intervención. Es el error más caro.
- *¿Por qué la precision bajó?* → Trade-off: al subir Recall aumentan falsas
  alarmas. Aceptable porque retener de más cuesta poco vs. perder un cliente.

**Sobre decisiones técnicas (indicador 10):**
- *¿Por qué Random Forest?* → Ensemble robusto, maneja no linealidad y desbalance,
  menos sobreajuste que un árbol único; ganó en AUC/Gini.
- *¿Cómo manejaron el desbalance?* → `class_weight='balanced'` + selección por
  Recall + (propuesta) SMOTE.
- *¿Por qué escalaron sólo para la regresión logística?* → Los árboles no
  dependen de la escala; la regresión sí (gradiente).

**Sobre seguridad (indicador 9, 30%):**
- *¿Qué datos son sensibles y cómo los protegen?* → `edad` (personal) y el score
  (perfilamiento); seudonimización, generalización por rol y RBAC.
- *¿Cómo cumplen la ley chilena?* → 19.628 (finalidad, proporcionalidad,
  seguridad) y 21.719 (consentimiento, ARCO+, no decisión automatizada).
- *¿La 21.663 no era la ley de datos?* → No, esa es la de ciberseguridad; la de
  datos personales es la 21.719 (corrección respecto al Parcial 2).

**Sobre integración n8n y BI (indicador 6, 5%):**
- *¿Cómo se integra el pipeline con n8n?* → El pipeline genera `clientes_scoreados.csv`; el workflow n8n lo lee, parsea y hace UPSERT a PostgreSQL. El workflow está exportado como JSON en `nexora-ml/n8n_workflows/`.
- *¿Qué ventaja da n8n frente a ejecutar el pipeline manualmente?* → Automatización: n8n puede programar la ejecución diaria, disparar por webhook o encadenar con otras herramientas (Slack, email) sin intervención humana.
- *¿Cómo se despliega en la nube?* → Con el Dockerfile provisto, se construye la imagen y se despliega en Azure Container Apps / AWS ECS / Google Cloud Run; el dashboard Streamlit queda accesible en el puerto 8501.

**Sobre mejoras (indicador 10, 10%):**
- *¿Cómo implementarían SMOTE?* → Sobre-muestreo sintético de la clase minoritaria
  sólo en train (nunca en test), con `imblearn`, midiendo el efecto en Precision/Recall.
- *¿Cómo evitarían la degradación del modelo?* → Monitoreo de *data drift* +
  reentrenamiento programado + versionado del modelo.
