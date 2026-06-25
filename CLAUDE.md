# CLAUDE.md — Contexto del proyecto NEXORA · EntrenamientoAI

Guía para asistentes de IA (Claude Code) que trabajen en este repositorio.
Lee también el [`README.md`](README.md) para la documentación de uso.

## Qué es

Servicio de **inteligencia predictiva de churn** de NEXORA. Es a la vez:

1. Un **pipeline DataOps batch** (`pipeline.py`) — ingesta multi-fuente →
   transformación → validación → scoring IA → seudonimización → carga Neon → KPIs.
2. Una **API REST FastAPI** (`api/main.py`) — expone entrenamiento y scoring como
   servicio web desplegable en Render.

Ambos comparten el módulo de IA en `nexora-ml/`. Es la entrega de la **Evaluación
Parcial 3** (ITY1101 · DUOC UC): exige modelo IA, matriz de confusión, accuracy,
recall, precision, F1, ROC-AUC, Gini, logs de rendimiento, seguridad y dashboard BI.

## Estructura clave

| Ruta | Rol |
|------|-----|
| `pipeline.py` | Orquestador batch. **No romper:** debe correr con `python pipeline.py`. |
| `api/main.py` | API FastAPI. Endpoints: `/health`, `/train`, `/score`, `/metrics`, `/predictions`. |
| `nexora-ml/src/entrenamiento.py` | `main()` entrena, evalúa y persiste modelo + métricas + figuras. |
| `nexora-ml/src/integracion_pipeline.py` | `ejecutar_scoring()` (batch) y `puntuar_dataframe()` (online). |
| `nexora-ml/src/preprocesamiento.py` | Calidad de datos, partición estratificada, escalado. |
| `nexora-ml/src/persistencia.py` | **Centraliza** métricas/predicciones → `reports/` (JSON/CSV) + Neon opcional. |
| `nexora-ml/src/seguridad.py` | Seudonimización SHA-256, generalización de edad, RBAC. |
| `nexora-ml/src/visualizaciones.py` | Figuras EDA + evaluación. Backend `Agg` (headless). |
| `nexora-ml/dashboard/app.py` | Dashboard BI en Streamlit. |
| `carga/neon_connection.py` | **Punto único** de resolución de la BD: `resolver_database_url()`. |
| `utils/logger_setup.py` | Logging estructurado compartido. |

## Convenciones y decisiones de diseño

- **Imports del módulo IA:** `api/main.py` y `pipeline.py` añaden `nexora-ml/src` a
  `sys.path` y luego importan por nombre (`import entrenamiento`, `import persistencia`,
  etc.). Mantener ese patrón.
- **Rutas:** siempre relativas vía `Path(__file__).resolve().parents[...]`. **Nunca**
  rutas absolutas de Windows ni credenciales hardcodeadas.
- **Base de datos:** resolver SIEMPRE con `carga.neon_connection.resolver_database_url()`,
  que lee `DATABASE_URL` → `DB_URL` → `NEON_DATABASE_URL` (en ese orden). `persistencia.py`
  delega ahí, con un fallback local equivalente para ejecución aislada del módulo IA.
- **Persistencia dual (best-effort):** `persistencia.py` siempre escribe archivos en
  `reports/`; la BD (tablas `ml_metricas`, `ml_predicciones`) es opcional — si no hay
  URL o falla, se loguea warning y se continúa. No hacer la BD obligatoria en la API.
- **Seguridad de la API:** si `ML_API_KEY` está en el entorno, `POST /train` y
  `POST /score` exigen cabecera `X-API-Key` (dependencia `verificar_api_key`). Si no,
  abiertos (dev local).
- **Logs de rendimiento:** middleware en `api/main.py` registra duración por request
  (`X-Process-Time-ms` + `nexora-ml/logs/api.log`). Entrenamiento/scoring loguean su
  tiempo en `nexora-ml/logs/`.
- **Endpoints pesados:** `/train` y `/score` se definen como `def` (no `async`) para
  que FastAPI los ejecute en threadpool y no bloqueen el event loop. `main()` de
  entrenamiento tarda ~45-50s (GridSearchCV).
- **Modelo:** `nexora-ml/models/modelo_churn.pkl` se genera en runtime (gitignored y
  excluido de la imagen Docker). Tras desplegar, ejecutar `POST /train` una vez antes
  de `POST /score`.

## Dependencias y entorno

- **Python 3.11.** `requirements.txt` (pipeline + API) y `nexora-ml/requirements.txt`
  (módulo IA). El módulo IA pina versiones más nuevas (numpy 2.2.6, scikit-learn 1.9.0);
  el `Dockerfile` instala root primero y luego nexora-ml, de modo que esas ganan.
- **FastAPI/uvicorn** en `requirements.txt` (`fastapi>=0.110,<1.0`, `uvicorn[standard]`).
  Nota: un entorno con fastapi 0.110 antiguo + starlette nuevo (1.3.x) rompe; en build
  limpio pip resuelve fastapi ~0.138 coherente con starlette 1.3.x.
- **Docker:** `python:3.11-slim`; arranca `uvicorn api.main:app --host 0.0.0.0
  --port ${PORT:-8000}`. Render inyecta `$PORT`.

## Cómo verificar cambios

```bash
# API end-to-end sin levantar servidor (TestClient)
python -c "from fastapi.testclient import TestClient; from api.main import app; \
print(TestClient(app).get('/health').json())"

# Pipeline batch (requiere DATABASE_URL para la etapa de carga Neon)
python pipeline.py

# Entrenamiento aislado (sin BD)
python nexora-ml/src/entrenamiento.py
```

Tras `POST /train` deben existir: `nexora-ml/models/modelo_churn.pkl`,
`nexora-ml/reports/metricas.json`, figuras en `nexora-ml/reports/figures/`.
Tras `POST /score`: `nexora-ml/reports/predicciones.{json,csv}`.

## Integración con `nexora-backend`

`nexora-backend` (API de negocio) consume este servicio: comparte la BD Neon
(`ml_metricas` / `ml_predicciones`) y/o llama vía HTTP a `/score`, `/metrics`,
`/predictions` autenticando con `X-API-Key` (`ML_API_KEY` compartida). El
reentrenamiento se dispara aparte (cron/manual) sin afectar las lecturas.

## Reglas al modificar

- No romper `python pipeline.py` (ejecución batch/cron/local).
- No introducir credenciales en código ni rutas absolutas.
- Mantener la lógica de scoring en `puntuar_dataframe()` (única fuente; la usan batch y online).
- Cambios de persistencia → pasar por `persistencia.py`, no duplicar escritura de archivos.
