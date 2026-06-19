from __future__ import annotations

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)


def obtener_conexion_neon():
    conn_str = os.getenv("NEON_DATABASE_URL")
    if not conn_str:
        raise ValueError(
            "NEON_DATABASE_URL no está configurada en el archivo .env"
        )
    conn = psycopg2.connect(conn_str)
    conn.autocommit = False
    return conn
