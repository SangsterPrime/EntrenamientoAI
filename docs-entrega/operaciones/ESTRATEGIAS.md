# Estrategias de Corrección de Anomalías y Escalabilidad
## NEXORA — Pipeline DataOps + IA

---

## 1. Estrategias de Corrección de Anomalías

### 1.1 Fallo de conexión API (OpenLibrary / Open-Meteo)

| Síntoma | Causa posible | Estrategia de corrección |
|---------|--------------|--------------------------|
| Lectura devuelve DataFrame vacío | API caída, rate limit, timeout | **Reintento exponencial:** capturar excepción `requests.RequestException`, reintentar con backoff (1s, 2s, 4s), máximo 3 intentos. Si persiste, usar datos caché de la última ejecución exitosa (`IA_Proyecto/data/cache/*.json`). |
| HTTP 429 (Too Many Requests) | Rate limit excedido | Insertar `time.sleep(1)` entre requests y respetar header `Retry-After`. En producción: cola de mensajes (RabbitMQ / Redis Queue) para desacoplar ingesta. |
| HTTP 503 (Service Unavailable) | API en mantención | Degradación graceful: el pipeline continúa con las fuentes disponibles y registra una alerta en KPIs (`disponibilidad_api_clima = False`). |

**Implementación actual:** `ingestion/leer_batch.py` y `ingestion/fuente_realtime.py` usan `try/except` con logging de error. Mejora propuesta: incorporar `tenacity` para reintentos automáticos.

### 1.2 Datos inconsistentes o fuera de rango

| Síntoma | Causa posible | Estrategia de corrección |
|---------|--------------|--------------------------|
| Valores nulos en Age/Fare | Registros incompletos en CSV | **Imputación:** mediana para variables numéricas (robusta a outliers), moda para categóricas. Implementado en `procesamiento/transformacion.py`. |
| Columna `2urvived` con valores fuera de {0,1} | Error de tipeo en fuente | **Validación semántica:** filtro `df["2urvived"].isin({0,1})` con logging de filas rechazadas. Si la columna no existe, el pipeline falla temprano con mensaje claro. |
| Edad negativa o > 120 | Error de captura | **Regla de negocio:** clamp al rango [0, 120] + alerta en KPIs (`completitud_titanic` baja). |
| Títulos de libros con caracteres no latinos | Datos multilingüe | **Filtro de alfabeto latino** implementado en `data_quality/validacion.py` con regex `^[a-zA-Z0-9\s\.,!\?\-\(\)áéíóúÁÉÍÓÚñÑ]+$`. |

### 1.3 Fallo en el scoring del modelo IA

| Síntoma | Causa posible | Estrategia de corrección |
|---------|--------------|--------------------------|
| `FileNotFoundError: No existe model_churn.pkl` | Modelo no entrenado | **Validación temprana:** verificar existencia del `.pkl` al inicio de `ejecutar_scoring()`. Si falta, ejecutar `entrenamiento.py` automáticamente o usar modelo fallback con reglas de negocio (ej: si reclamos > 5 → riesgo ALTO). |
| Error de dimensión en `predict_proba` | Columnas no coinciden | **Versionado de esquema:** persistir `paquete["columnas"]` junto al modelo y hacer `X = cartera[columnas]` para alinear siempre. |
| Probabilidades NaN | Datos con nulos no imputados | **Doble validación:** imputar nulos *antes* del scoring (`prep.imputar_nulos(cartera)`) y verificar `X.isna().sum().sum() == 0`. |

### 1.4 Error en carga SQLite

| Síntoma | Causa posible | Estrategia de corrección |
|---------|--------------|--------------------------|
| `sqlite3.OperationalError: database is locked` | Acceso concurrente | Activar WAL mode (`PRAGMA journal_mode=WAL;`) para lecturas concurrentes sin bloqueo. |
| Violación de clave primaria | Duplicados | Usar `INSERT OR REPLACE` (implementado) para garantizar idempotencia. |
| Ruta de base de datos no existe | Directorio faltante | `DIR_DATA.mkdir(parents=True, exist_ok=True)` antes de abrir conexión (implementado). |

### 1.5 Estrategia de detección y diagnóstico general

```
1. DETECTAR → logging estructurado atrapa toda excepción con 
   timestamp + módulo + mensaje de error
2. DIAGNOSTICAR → el KPI de alerta (WARNING/CRITICAL) indica 
   la gravedad y el componente afectado
3. CORREGIR → según la tabla de estrategias arriba (reintento, 
   imputación, fallback, etc.)
4. REGISTRAR → log_audit() en security/config.py deja trazabilidad 
   de la corrección aplicada
```

---

## 2. Estrategias de Escalabilidad

### 2.1 Escalabilidad horizontal (más datos)

| Componente | Estrategia | Tecnología propuesta |
|------------|-----------|---------------------|
| **Ingesta CSV** | Particionar archivos grandes en chunks y procesar en paralelo con `concurrent.futures.ProcessPoolExecutor` | `pandas.read_csv(chunksize=10000)` + multiprocessing |
| **Ingesta API** | Distribuir requests entre workers asíncronos | `asyncio` + `aiohttp` (en vez de `requests` síncrono) |
| **Transformación** | Vectorizar operaciones con pandas/numpy; si no cabe en RAM, usar Dask | `dask.dataframe` para DataFrames out-of-core |
| **Validación** | Paralelizar filtros por partición de datos | `pandas.groupby().apply()` con `group_keys=False` |
| **Scoring IA** | Batch prediction vectorizada (ya implementada con `predict_proba`) | `joblib.Parallel(n_jobs=-1)` para múltiples modelos |
| **Carga SQLite** | Transacciones batch (commit cada 1000 filas) en vez de una por una | `executemany()` + commit periódico |

### 2.2 Escalamiento a PostgreSQL (producción)

SQLite es adecuado para prototipado y demo. En producción se migra a PostgreSQL:

```python
# Estrategia de migración SQLite → PostgreSQL
# 1. Reemplazar sqlite3 con psycopg2
# 2. Usar INSERT ... ON CONFLICT (columna) DO UPDATE SET ... (UPSERT real)
# 3. Activar conexión pool con SQLAlchemy + PGBouncer
# 4. Índices: CREATE INDEX ON titanic_clean (Passengerid)
```

| Capacidad | SQLite | PostgreSQL |
|-----------|--------|------------|
| Volumen máximo | ~100 GB (único escritor) | ~TB (múltiples escritores) |
| Concurrencia | 1 escritor | Ilimitada (conexiones pool) |
| Réplicas | No | Streaming replication |
| Particionamiento | No | Table partitioning por fecha |

### 2.3 Escalabilidad del modelo IA

| Técnica | Descripción | Cuándo aplica |
|---------|-------------|---------------|
| **Reentrenamiento incremental** | Actualizar el modelo con nuevos datos sin reentrenar desde cero | Cuando hay data drift detectado |
| **Modelo en API REST** | Servir scoring como microservicio (FastAPI + Docker) | Cuando múltiples pipelines consumen scoring |
| **Cache de predicciones** | Almacenar resultados previos para evitar rescorear clientes sin cambios | Cartera estable entre ejecuciones |
| **Versionado de modelos (MLflow)** | Registrar métricas, artefactos y parámetros por versión | Cuando hay múltiples versiones en producción |

### 2.4 Monitoreo de cuello de botella

```
1. LATENCIA → cada etapa mide su duración (time.perf_counter())
   y la reporta en KPIs. Si > umbral → alerta WARNING/CRITICAL.
2. MEMORIA → monitorear con psutil si el pipeline corre en servidor.
   Si RSS > 80% RAM → reducir batch size o migrar a procesamiento 
   streaming (Apache Kafka + Spark Streaming).
3. THROUGHPUT → medir filas/segundo en cada etapa. Si hay 
   degradación → identificar etapa más lenta y optimizar (ej: 
   vectorizar loop, agregar índice).
```
