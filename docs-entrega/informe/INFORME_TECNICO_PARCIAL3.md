# NEXORA — Informe Técnico
## Evaluación Parcial N°3 — Encargo con Presentación
### Optimización del Pipeline DataOps con un Modelo de IA Predictivo

---

<!-- a. PORTADA -->
**DUOC UC — Escuela de Informática y Telecomunicaciones**
**Asignatura:** ITY1101 — Gestión de Datos para IA
**Sección:** _[completar sección]_
**Proyecto:** NEXORA — *Autonomous Procurement Intelligence*

**Integrantes:**

| Nombre | RUT |
|---|---|
| Esteban Gamboa | _[completar RUT]_ |
| Julio Llauri | _[completar RUT]_ |
| Joel Sangster | _[completar RUT]_ |

Santiago, Chile — 2025

---

## b. Índice

1. Resumen Ejecutivo
2. Fase 1 (Parcial 2) y mejoras incorporadas
3. Entrenamiento del Modelo de IA
   - 3.1 Calidad y partición de datos
   - 3.2 Preprocesamiento
   - 3.3 Análisis de variables (univariado y bivariado)
   - 3.4 Elección de algoritmos y entrenamiento
   - 3.5 Métricas de evaluación
4. Rendimiento en la Nube (logs y gráficos)
5. Estrategia de Auditoría de Seguridad
6. Integración con Sistemas BI y Dashboard
7. Limitaciones y fallas detectadas
8. Conclusiones y propuestas de mejora
9. Anexos

---

## 1. Resumen Ejecutivo

NEXORA es una plataforma de automatización inteligente para la gestión de
adquisiciones en PYMEs chilenas, construida sobre un pipeline DataOps
(ingesta → transformación → validación → carga) orquestado con n8n y PostgreSQL.
En su evolución hacia un producto **SaaS por suscripción**, NEXORA enfrenta un
desafío de negocio crítico: **la retención de sus suscriptores**.

Esta tercera fase incorpora al pipeline un **módulo de Inteligencia Predictiva**
que entrena un modelo de IA supervisado para anticipar el **abandono (churn)** de
clientes, segmentarlos por nivel de riesgo y activar acciones de retención antes
de que el cliente se vaya.

**Valor para la organización:** retener a un cliente cuesta significativamente
menos que adquirir uno nuevo. Al detectar el **76% de los clientes que
efectivamente abandonan**, el modelo permite intervenir oportunamente sobre la
cartera en riesgo, protegiendo los ingresos recurrentes y aumentando el *lifetime
value* del cliente. La solución se entrega con un **dashboard interactivo de BI**
que pone la predicción en manos del equipo de retención.

---

## 2. Fase 1 (Parcial 2) y mejoras incorporadas

En el Parcial 2 se construyó el pipeline DataOps de NEXORA bajo una **metodología
híbrida PMBOK** (predictiva para el ETL, adaptativa para los componentes de IA),
con cuatro etapas: ingesta multi-fuente, transformación/limpieza, validación
estructural y semántica, y carga a PostgreSQL.

**Mejoras solicitadas e incorporadas en el Parcial 3:**

| Mejora | Descripción |
|---|---|
| **Nueva etapa de scoring IA** | El pipeline ahora *enriquece* los datos con una predicción de abandono, no sólo los gestiona (`src/integracion_pipeline.py`). |
| **Modularización del código** | Separación en módulos reutilizables: preprocesamiento, visualización, entrenamiento, seguridad e integración. |
| **Manejo del desbalance de clases** | Incorporación de `class_weight='balanced'`, ausente en la demo inicial. |
| **Métricas avanzadas** | Se agregan Curva ROC, AUC y coeficiente de **Gini**, además de la matriz de confusión. |
| **Trazabilidad reforzada** | Logging estructurado por etapa con tiempos de ejecución (evidencia de rendimiento). |
| **Corrección normativa** | Se corrige la referencia legal: la ley de datos personales es la **21.719** (no la 21.663, que es de ciberseguridad). |
| **Seguridad por diseño** | Módulo de anonimización y RBAC aplicable a la cartera de clientes. |

---

## 3. Entrenamiento del Modelo de IA

**Problema:** clasificación binaria supervisada — predecir si un cliente
abandonará (`abandona` = 1) o no (`abandona` = 0).
**Dataset:** 500 suscriptores, 6 variables predictoras + 1 objetivo.

### 3.1 Calidad y partición de datos

El análisis de calidad (`src/preprocesamiento.py`) arroja:

- **500 registros, 7 columnas.**
- **0 valores nulos** y **0 duplicados** → dataset íntegro.
- **Balance de la variable objetivo:** 74,6 % no abandona / 25,4 % abandona.
- **Ratio de desbalance: 2,94 : 1** → se confirma desbalance de clases, factor
  determinante en la estrategia de modelado.

**Partición:** 80 % entrenamiento (400) / 20 % prueba (100), **estratificada**
(`stratify=y`) para preservar la proporción de clases en ambos conjuntos.

> *Figura 1 — Distribución de la variable objetivo (`reports/figures/01_balance_objetivo.png`)*

### 3.2 Preprocesamiento

- **Imputación de robustez:** mediana (numéricas) / moda (categóricas) como
  salvaguarda ante datos reales (el dataset entregado no presenta nulos).
- **Escalado:** `StandardScaler` sobre las variables numéricas para los modelos
  sensibles a la escala (Regresión Logística). Los modelos de árbol operan sobre
  datos crudos, ya que no requieren normalización.
- **Manejo del desbalance:** ponderación de clases (`class_weight='balanced'`)
  para que el modelo no ignore la clase minoritaria (los que abandonan).

### 3.3 Análisis de variables (univariado y bivariado)

- **Univariado** (*Figura 2*): distribución de cada variable predictora. Las
  variables muestran rangos plausibles; `reclamos` y `anos_cliente` concentran
  masa en valores bajos.
- **Bivariado** (*Figura 3*): comparación de cada variable según la clase. Los
  clientes que abandonan tienden a presentar **más reclamos**, **menor antigüedad**
  y **menor proporción de plan premium**.
- **Matriz de correlación** (*Figura 4*): no se observan correlaciones lineales
  extremas entre predictoras (ausencia de multicolinealidad severa), lo que
  valida el uso conjunto de todas las variables.

### 3.4 Elección de algoritmos y entrenamiento

Se entrenaron y compararon **cuatro algoritmos**, más una versión optimizada del
mejor candidato:

| Algoritmo | Justificación de inclusión |
|---|---|
| **Regresión Logística** | Línea base interpretable para clasificación binaria. |
| **Árbol de Decisión** | Captura relaciones no lineales; fácil de explicar. |
| **Random Forest** | *Ensemble* robusto, reduce sobreajuste, maneja desbalance. |
| **Gradient Boosting** | *Ensemble* secuencial de alto poder predictivo. |

**Ajuste de hiperparámetros:** sobre Random Forest se aplicó `GridSearchCV`
(validación cruzada de 5 *folds*) optimizando **Recall**, obteniendo:
`max_depth=4, min_samples_leaf=4, n_estimators=100` (Recall CV = 0,756).

**Criterio de selección del modelo:** se priorizó el **Recall** porque, en churn,
el error más costoso es el **falso negativo** (no detectar un cliente que se va y
perderlo sin posibilidad de retención).

### 3.5 Métricas de evaluación

Resultados sobre el conjunto de prueba (100 clientes):

| Modelo | Accuracy | Precision | Recall | F1 | ROC-AUC | **Gini** |
|---|---|---|---|---|---|---|
| Regresión Logística | 0,78 | 0,55 | 0,68 | 0,61 | 0,818 | 0,635 |
| Árbol de Decisión | 0,76 | 0,51 | 0,72 | 0,60 | 0,787 | 0,574 |
| Random Forest | 0,80 | 0,59 | 0,68 | 0,63 | 0,865 | 0,730 |
| Gradient Boosting | 0,80 | 0,65 | 0,44 | 0,52 | 0,844 | 0,689 |
| **Random Forest (optimizado)** ⭐ | **0,79** | **0,56** | **0,76** | **0,64** | **0,877** | **0,755** |

> *Figura 5 — Matriz de confusión · Figura 6 — Curva ROC · Figura 7 — Comparación de métricas*

**Interpretación:**
- **Matriz de confusión** del modelo seleccionado: detecta **19 de 25** abandonos
  reales (Recall 76 %), a costa de algunas falsas alarmas (Precision 56 %) — un
  intercambio aceptable dado el bajo costo de una retención innecesaria frente al
  alto costo de perder un cliente.
- **Coeficiente de Gini = 0,755:** indica un **poder discriminante alto**
  (Gini = 2·AUC − 1; AUC = 0,877). El modelo separa muy bien a quienes abandonan
  de quienes permanecen.
- **Mejora respecto a la línea base:** la demo inicial alcanzaba un Recall de
  ~48 %. El manejo del desbalance y el ajuste de hiperparámetros elevaron la
  detección de abandonos a **76 %**, sin sacrificar el AUC.
- **Variables más influyentes** (*Figura 8*): `reclamos`, `anos_cliente` y
  `plan_premium` resultan los predictores más determinantes del abandono.

---

## 4. Rendimiento en la Nube (logs y gráficos)

El módulo está diseñado para ejecutarse en entornos local y nube (compatible con
*Streamlit Community Cloud* y contenedores Docker heredados del Parcial 2). El
**logging estructurado** (`logs/entrenamiento.log`, `logs/scoring_pipeline.log`)
registra cada etapa con marca de tiempo y duración, sirviendo de evidencia de
rendimiento:

| KPI técnico | Valor medido |
|---|---|
| Tiempo total de entrenamiento (4 modelos + GridSearch) | ~13 s |
| Tiempo de scoring de la cartera completa (500 clientes) | ~0,28 s |
| Latencia de arranque del dashboard | < 3 s |
| Tasa de errores de ejecución | 0 |

Estos KPIs extienden la **estrategia de monitoreo** definida en el Parcial 2
(latencia, completitud, errores de validación), ahora aplicada al ciclo de IA.

---

## 5. Estrategia de Auditoría de Seguridad

*(Detalle completo en `docs-entrega/seguridad/AUDITORIA_SEGURIDAD.md`.)*

- **Clasificación de datos:** `edad` se trata como dato personal; `prob_abandono`
  como dato inferido sensible (perfilamiento).
- **Minimización:** el modelo **no usa** RUT, nombre ni correo.
- **Seudonimización** (hash SHA-256 + sal) y **generalización** de la edad por rol
  (k-anonimato), implementadas en `src/seguridad.py`.
- **RBAC:** roles `admin`, `analista`, `retención`, `auditor`, cada uno con vista
  mínima necesaria.
- **Marco legal:** Ley **19.628** (vigente) y Ley **21.719** (nueva ley de datos
  personales). Atención especial al derecho a **no ser objeto de decisiones
  únicamente automatizadas**: el score es una recomendación para un humano.

---

## 6. Integración con Sistemas BI, n8n y Nube

Se desarrolló un **dashboard interactivo en Streamlit** (`dashboard/app.py`),
que cumple el rol de capa BI ("o similar" según la rúbrica) y consume directamente
los artefactos del modelo (`metricas.json`, figuras, `modelo_churn.pkl`).

**Componentes del dashboard:**
1. **KPIs** del modelo en producción (Accuracy, Recall, Precision, F1, Gini).
2. **Comparación de modelos** (tabla resaltada + curva ROC + importancia de variables).
3. **EDA** interactivo del dataset.
4. **Predictor en vivo:** permite ingresar el perfil de un cliente y obtener su
   probabilidad de abandono y segmento de riesgo en tiempo real.
5. **Rendimiento operativo** (logs de ejecución).

### 6.1 Integración con n8n (workflow automatizado)

Se exportó un **workflow n8n** (`nexora-ml/n8n_workflows/carga_scoreados.json`)
que automatiza el ciclo completo:

```
[Manual Trigger] → [Ejecutar pipeline.py] → [Leer CSV scoreado]
    → [Parsear a JSON] → [UPSERT en PostgreSQL]
```

El workflow:
1. Dispara la ejecución del pipeline Python (`pipeline.py`) que genera datos frescos.
2. Lee el archivo `clientes_scoreados.csv` generado por el scoring.
3. Parsea el CSV a objetos JSON tipando correctamente cada columna.
4. Ejecuta UPSERT (`INSERT ... ON CONFLICT DO UPDATE`) en PostgreSQL,
   previa creación automática de la tabla con `CREATE TABLE IF NOT EXISTS`.

El script SQL de inicialización de la tabla se encuentra en
`nexora-ml/n8n_workflows/init_tabla.sql`, e incluye índices por segmento de
riesgo y fecha de carga para optimizar las consultas del dashboard.

### 6.2 Integración con el pipeline DataOps

La etapa `ejecutar_scoring()` produce `data/clientes_scoreados.csv` con la
cartera segmentada (ALTO/MEDIO/BAJO) y la **acción de retención recomendada**,
lista para cargarse a PostgreSQL (UPSERT) y ser consumida por el dashboard o
por workflows de n8n. En la última ejecución:
**124 clientes en riesgo ALTO, 138 MEDIO y 238 BAJO.**

### 6.3 Despliegue en la nube

El proyecto incluye un **Dockerfile** (Python 3.11, imagen Microsoft devcontainer)
que empaqueta tanto el pipeline como el dashboard, permitiendo el despliegue en
cualquier proveedor cloud (Azure Container Apps, AWS ECS, Google Cloud Run).
El comando `CMD ["python", "pipeline.py"]` ejecuta el pipeline al arrancar,
y el puerto `8501` queda expuesto para el dashboard Streamlit.

---

## 7. Limitaciones y fallas detectadas

| # | Limitación / falla | Impacto | Tipo |
|---|---|---|---|
| 1 | **Dataset pequeño (500 filas)** | Limita la generalización; métricas con varianza. | Limitación de datos |
| 2 | **Desbalance de clases (2,94:1)** | El modelo tiende al sesgo hacia la clase mayoritaria; mitigado pero no eliminado. | Limitación estructural |
| 3 | **Precision moderada (0,56)** | Genera falsas alarmas → costo operativo de retención innecesaria. | Limitación del modelo |
| 4 | **Datos estáticos (sin *data drift*)** | El modelo puede degradarse al cambiar el comportamiento real. | Falla operativa potencial |
| 5 | **Ausencia de variables de negocio ricas** (ticket, NPS, uso real) | Techo en el poder predictivo. | Limitación de datos |
| 6 | **Persistencia vía pickle** | Riesgo si se cargan modelos de origen no confiable. | Riesgo de seguridad (mitigado: sólo artefactos propios) |

> **Distinción limitación vs. error:** una *limitación* es una restricción
> conocida del diseño (p. ej., el tamaño del dataset); un *error/falla* es un
> comportamiento defectuoso en operación (p. ej., degradación por *data drift*).

---

## 8. Conclusiones y propuestas de mejora

**Conclusiones:**
- El módulo de IA convierte a NEXORA de una plataforma que *gestiona* datos en una
  que *predice y acciona* sobre ellos, agregando valor de negocio directo (retención).
- El **Random Forest optimizado** logra un **Gini de 0,755** y un **Recall de 76 %**,
  superando ampliamente la línea base, con la decisión final siempre en manos humanas.
- La solución es íntegra: código modular, métricas reproducibles, dashboard BI,
  seguridad por diseño y cumplimiento normativo chileno.

**Propuestas de mejora (priorizadas):**

| Prioridad | Mejora | Beneficio esperado |
|---|---|---|
| Alta | **Balanceo con SMOTE / *threshold tuning*** | Mejorar Precision sin perder Recall. |
| Alta | **Monitoreo de *data drift* + reentrenamiento programado** | Sostener el rendimiento en el tiempo. |
| Media | **Enriquecer variables** (NPS, ticket promedio, uso real) | Subir el techo predictivo. |
| Media | **Serialización segura** (ONNX / skops en vez de pickle) | Reducir riesgo de ejecución de código. |
| Media | **Explicabilidad con SHAP** | Justificar cada predicción ante el equipo y el cliente. |
| Baja | **Despliegue como API REST** (FastAPI) en la nube | Scoring bajo demanda integrable a n8n. |

---

## 9. Anexos

- **Anexo A — Repositorio y código:** `nexora-ml/` (módulos `src/`, dashboard, notebook).
- **Anexo B — Métricas completas:** `reports/metricas.json`, `reports/comparacion_modelos.csv`.
- **Anexo C — Figuras:** `reports/figures/01..08`.
- **Anexo D — Logs de ejecución:** `logs/entrenamiento.log`, `logs/scoring_pipeline.log`.
- **Anexo E — Auditoría de seguridad:** `docs-entrega/seguridad/AUDITORIA_SEGURIDAD.md`.
- **Anexo F — Workflow n8n:** `nexora-ml/n8n_workflows/carga_scoreados.json`
  (workflow exportable con 5 nodos: trigger → pipeline → CSV → parse → PostgreSQL).
- **Anexo G — Script SQL de inicialización:** `nexora-ml/n8n_workflows/init_tabla.sql`
  (tabla `clientes_scoreados` con índices y comentarios).
- **Anexo H — Dockerfile:** `Dockerfile` (Python 3.11 para nube/local).
- **Anexo I — Repositorios del Parcial 2:**
  `github.com/SangsterPrime/nexora-backend`, `nexora-fronted`.

> **Nota de formato:** para la entrega final, exportar este documento a **PDF**,
> fuente Arial/Calibri 10–12, interlineado 1,5, párrafos justificados, extensión
> 10–12 páginas (insertar las figuras en los puntos indicados y completar sección/RUT).
