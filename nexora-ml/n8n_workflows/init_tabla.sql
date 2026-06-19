-- NEXORA · Inicialización de tabla clientes_scoreados en PostgreSQL
-- Ejecutar antes del primer uso del workflow n8n carga_scoreados.json

CREATE TABLE IF NOT EXISTS public.clientes_scoreados (
    id              SERIAL PRIMARY KEY,
    edad            INTEGER,
    anos_cliente    INTEGER,
    uso_datos_gb    REAL,
    llamadas_mes    INTEGER,
    reclamos        INTEGER,
    plan_premium    INTEGER,
    abandona        INTEGER,
    prob_abandono   REAL,
    segmento_riesgo TEXT,
    accion_retencion TEXT,
    fecha_carga     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para búsqueda por segmento (consultas del dashboard BI)
CREATE INDEX IF NOT EXISTS idx_clientes_scoreados_segmento
    ON public.clientes_scoreados (segmento_riesgo);

-- Índice para filtrar por fecha de carga (monitoreo)
CREATE INDEX IF NOT EXISTS idx_clientes_scoreados_fecha
    ON public.clientes_scoreados (fecha_carga);

COMMENT ON TABLE public.clientes_scoreados IS
    'Clientes scoreados por el modelo de IA de NEXORA. Poblado por n8n desde pipeline.py cada ejecución.';
COMMENT ON COLUMN public.clientes_scoreados.prob_abandono IS
    'Probabilidad de abandono (0-1) generada por Random Forest optimizado. Dato inferido sensible (Ley 21.719).';
COMMENT ON COLUMN public.clientes_scoreados.segmento_riesgo IS
    'Segmento: ALTO (>=0.60), MEDIO (>=0.35), BAJO (<0.35).';
COMMENT ON COLUMN public.clientes_scoreados.accion_retencion IS
    'Acción recomendada según segmento para el equipo de retención.';
