# NEXORA · EntrenamientoAI — Pipeline DataOps + IA + API

Servicio de **inteligencia predictiva de churn** (abandono de suscriptores) para
la plataforma NEXORA. Combina un **pipeline DataOps batch** (ingesta → procesamiento
→ validación → scoring IA → carga Neon) con una **API REST (FastAPI)** desplegable
en **Render**, manteniendo intacta la ejecución local/cron.

> Evaluación Parcial 3 · ITY1101 Gestión de Datos para IA · DUOC UC

---

## Arquitectura

```
EntrenamientoAI/
├── api/main.py              # API REST FastAPI (servicio web · Render)
├── pipeline.py              # Pipeline DataOps batch (python pipeline.py · cron/local)
├── ingestion/              # Ingesta multi-fuente (CSV, batch, tiempo real)
├── procesamiento/          # Transformaciones
├── data_quality/           # Validación estructural/semántica
├── security/               # Seudonimización, RBAC, auditoría
├── monitoring/             # KPIs del pipeline
├── carga/                  # Carga a Neon (PostgreSQL) · neon_connection.py centraliza la BD
├── utils/                  # Logging estructurado compartido
└── nexora-ml/              # Módulo de Inteligencia Predictiva
    ├── src/
    │   ├── entrenamiento.py        # Entrena, evalúa y persiste el modelo
    │   ├── preprocesamiento.py     # Calidad de datos, partición, escalado
    │   ├── integracion_pipeline.py # Scoring (etapa del pipeline + scoring online)
    │   ├── persistencia.py         # Centraliza métricas/predicciones → reports/ + Neon
    │   ├── seguridad.py            # Anonimización / enmascaramiento / RBAC
    │   └── visualizaciones.py      # Figuras EDA + evaluación (backend Agg, headless)
    ├── dashboard/app.py            # Dashboard BI (Streamlit)
    ├── models/                     # modelo_churn.pkl (generado por el entrenamiento)
    ├── reports/                    # metricas.json, predicciones.*, figures/*.png
    └── data/                       # dataset_churn_telecomunicaciones.csv
```

**El modelo:** clasificación binaria de churn. Compara Regresión Logística, Árbol
de Decisión, Random Forest y Gradient Boosting; ajusta hiperparámetros con
GridSearchCV (optimiza Recall, clave en churn) y selecciona el mejor modelo.
Métricas exigidas: **accuracy, precision, recall, F1, ROC-AUC y Gini** (= 2·AUC − 1),
más matriz de confusión y curva ROC.

---

## Ejecución local

### 1. Instalar dependencias

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
pip install -r nexora-ml/requirements.txt
```

### 2. Configurar entorno

```bash
cp .env.example .env          # Windows: copy .env.example .env
# Edita .env con tu DATABASE_URL (Neon) si vas a usar carga/persistencia en BD.
```

### 3a. Pipeline batch (DataOps completo · cron/local)

```bash
python pipeline.py
```

Ejecuta ingesta → transformación → validación → scoring IA → seudonimización →
carga Neon → KPIs. **Requiere `DATABASE_URL`** (la etapa de carga escribe en Neon).

### 3b. Entrenamiento / scoring aislados (sin BD)

```bash
python nexora-ml/src/entrenamiento.py        # entrena y genera reports/figures
python nexora-ml/src/integracion_pipeline.py # scoring de la cartera
```

### 3c. API REST (servicio web)

```bash
uvicorn api.main:app --reload --port 8000
```

Docs interactivas (Swagger): <http://localhost:8000/docs>

### 3d. Dashboard BI (Streamlit)

```bash
streamlit run nexora-ml/dashboard/app.py
```

---

## Ejecución con Docker

```bash
# Construir la imagen
docker build -t nexora-ai .

# Levantar el servicio web (API en el puerto 8000)
docker run -p 8000:8000 --env-file .env nexora-ai
```

La imagen usa **Python 3.11 slim**, instala las dependencias del pipeline + IA + API
y levanta `uvicorn api.main:app`. El puerto se toma de `${PORT:-8000}` (compatible
con Render, que inyecta `$PORT`).

---

## Despliegue en Render (Web Service)

1. **New → Web Service** y conecta este repositorio.
2. **Environment:** `Docker` (Render detecta el `Dockerfile`).
3. **Variables de entorno** (Settings → Environment):

   | Variable        | Descripción                                              |
   |-----------------|----------------------------------------------------------|
   | `DATABASE_URL`  | Cadena de conexión a Neon (PostgreSQL). Opcional.        |
   | `ML_API_KEY`    | Clave para proteger `POST /train` y `POST /score`.       |
   | `ENVIRONMENT`   | `render` / `production`.                                 |

   > No definas `PORT`: Render lo inyecta automáticamente y el contenedor lo usa.

4. **Deploy.** Render construye la imagen y expone la URL pública.
5. **Health check path:** `/health`.

> El `modelo_churn.pkl` no se incluye en la imagen (se genera en runtime). Tras el
> primer deploy, ejecuta `POST /train` una vez para entrenar y persistir el modelo;
> luego `POST /score` queda disponible. Si conectas Neon, métricas y predicciones
> también se guardan en las tablas `ml_metricas` / `ml_predicciones`.

---

## Endpoints

| Método | Ruta           | Descripción                                                        | Auth* |
|--------|----------------|--------------------------------------------------------------------|:-----:|
| GET    | `/health`      | Estado del servicio: entorno, modelo entrenado, BD configurada.    |  —    |
| POST   | `/train`       | Entrena el modelo: métricas, matriz de confusión, ROC, Gini, logs. |  ✔    |
| POST   | `/score`       | Scoring/predicción (online con cuerpo JSON, o batch sin cuerpo).   |  ✔    |
| GET    | `/metrics`     | Últimas métricas del modelo en JSON.                               |  —    |
| GET    | `/predictions` | Últimas predicciones / clientes scoreados (`?limite=N`).           |  —    |
| GET    | `/`            | Catálogo de endpoints.                                             |  —    |

\* **Auth:** si `ML_API_KEY` está definida en el entorno, los endpoints marcados
exigen la cabecera `X-API-Key: <clave>`. Si no está definida (desarrollo local),
quedan abiertos.

### Ejemplos

```bash
# Estado
curl http://localhost:8000/health

# Entrenar (con API key configurada)
curl -X POST http://localhost:8000/train -H "X-API-Key: $ML_API_KEY"

# Scoring online de perfiles
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" -H "X-API-Key: $ML_API_KEY" \
  -d '{"clientes":[{"edad":22,"anos_cliente":1,"uso_datos_gb":2.0,"llamadas_mes":90,"reclamos":4,"plan_premium":0}]}'

# Scoring batch (toda la cartera)
curl -X POST http://localhost:8000/score -H "X-API-Key: $ML_API_KEY"

# Últimas métricas y predicciones
curl http://localhost:8000/metrics
curl "http://localhost:8000/predictions?limite=10"
```

Respuesta típica de `/score` (online):

```json
{
  "status": "scoreado", "modo": "online", "total": 1,
  "resumen_riesgo": {"ALTO": 1},
  "predicciones": [{"edad": 22, "prob_abandono": 0.9353,
                    "segmento_riesgo": "ALTO",
                    "accion_retencion": "Contacto prioritario + oferta de retención"}],
  "tiempo_scoring_s": 0.055
}
```

---

## Conexión con `nexora-backend`

Este servicio es el **cerebro de IA** de la plataforma; `nexora-backend` (la API de
negocio) lo consume como un microservicio independiente:

- **Base de datos compartida (Neon).** Ambos apuntan a la misma instancia Neon
  mediante `DATABASE_URL`. `EntrenamientoAI` escribe métricas y predicciones en las
  tablas `ml_metricas` / `ml_predicciones`; `nexora-backend` las lee para mostrarlas
  en su frontend o accionar campañas de retención.
- **Vía HTTP (REST).** `nexora-backend` llama a los endpoints de este servicio:
  `POST /score` para puntuar clientes en tiempo real, `GET /metrics` para exponer el
  rendimiento del modelo y `GET /predictions` para listar la cartera scoreada.
  La autenticación se hace con la cabecera `X-API-Key` (`ML_API_KEY` compartida).
- **Desacople.** El reentrenamiento (`POST /train`, costoso) se dispara de forma
  programada (cron/manual) sin afectar el camino de lectura de `nexora-backend`.

```
                 ┌──────────────────────┐      HTTP /score /metrics      ┌────────────────┐
   Cliente  ───▶ │   nexora-backend     │ ─────────────────────────────▶│ EntrenamientoAI │
   (frontend)    │  (API de negocio)    │ ◀───────── JSON ──────────────│  (API IA · este)│
                 └──────────┬───────────┘                                └────────┬───────┘
                            │                Neon (PostgreSQL)                    │
                            └──────────────────────┬─────────────────────────────┘
                                       ml_metricas · ml_predicciones
```

---

## Variables de entorno

Ver [`.env.example`](.env.example). Resumen:

| Variable                 | Obligatoria | Descripción                                                      |
|--------------------------|:-----------:|------------------------------------------------------------------|
| `DATABASE_URL`           | Para BD     | Conexión Neon/PostgreSQL. Alias: `DB_URL`, `NEON_DATABASE_URL`.  |
| `ML_API_KEY`             | Recomendada | Protege `POST /train` y `POST /score`.                          |
| `ENVIRONMENT`            | No          | `local` / `docker` / `render` / `production`.                   |
| `NEXORA_SALT`            | No          | Sal del hash SHA-256 para seudonimización (Ley 19.628/21.719).  |

Sin credenciales hardcodeadas ni rutas absolutas: todas las rutas se resuelven
relativas al proyecto y los secretos provienen del entorno.

---

## Evidencia de rendimiento (nube/local)

- La API registra el tiempo de cada solicitud (`X-Process-Time-ms` y `nexora-ml/logs/api.log`).
- El entrenamiento y el scoring registran su duración en `nexora-ml/logs/`.
- `reports/metricas.json` incluye `tiempo_total_s` y los tiempos por modelo.
