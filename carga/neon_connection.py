from __future__ import annotations

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Orden de prioridad para resolver la cadena de conexión. Mantiene
# compatibilidad con el nombre histórico (NEON_DATABASE_URL) y admite los
# nombres estándar usados en Render / nexora-backend (DATABASE_URL, DB_URL).
_VARS_DB = ("DATABASE_URL", "DB_URL", "NEON_DATABASE_URL")


def resolver_database_url() -> str | None:
    """
    Devuelve la URL de conexión a PostgreSQL (Neon) leída del entorno.

    Punto único de verdad para todo el proyecto: API, pipeline y módulo IA
    resuelven la BD por aquí, sin credenciales embebidas en el código.
    """
    for var in _VARS_DB:
        valor = os.getenv(var)
        if valor:
            return valor
    return None


def obtener_conexion_neon():
    conn_str = resolver_database_url()
    if not conn_str:
        raise ValueError(
            "No hay URL de base de datos configurada. Define DATABASE_URL "
            "(o DB_URL / NEON_DATABASE_URL) en el archivo .env o en el entorno."
        )
    conn = psycopg2.connect(conn_str)
    conn.autocommit = False
    return conn
