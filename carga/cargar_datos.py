from __future__ import annotations

import time
from datetime import datetime, timedelta

import pandas as pd
import psycopg2

from carga.neon_connection import obtener_conexion_neon
from utils.logger_setup import configurar_logger

logger = configurar_logger(
    "carga.cargar_datos", archivo="load_database.log", consola=False
)


def _crear_tablas(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS proveedores (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                rut TEXT UNIQUE NOT NULL,
                email TEXT,
                reputacion_score REAL DEFAULT 0,
                historial_cumplimiento TEXT DEFAULT 'sin historial'
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solicitudes (
                id SERIAL PRIMARY KEY,
                producto TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                presupuesto_max REAL NOT NULL,
                urgencia TEXT DEFAULT 'normal',
                estado TEXT DEFAULT 'pendiente',
                proveedor_elegido_id INTEGER REFERENCES proveedores(id),
                ahorro_conseguido REAL DEFAULT 0,
                prob_abandono REAL DEFAULT 0,
                segmento_riesgo TEXT DEFAULT 'BAJO',
                accion_retencion TEXT DEFAULT 'Monitoreo estandar'
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cotizaciones (
                id SERIAL PRIMARY KEY,
                solicitud_id INTEGER NOT NULL REFERENCES solicitudes(id),
                proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
                precio_total REAL NOT NULL,
                plazo_dias INTEGER,
                garantia_meses INTEGER,
                risk_score REAL DEFAULT 0,
                estado TEXT DEFAULT 'recibida',
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS negociaciones (
                id SERIAL PRIMARY KEY,
                cotizacion_id INTEGER NOT NULL REFERENCES cotizaciones(id),
                ronda INTEGER NOT NULL,
                email_enviado TEXT,
                email_recibido TEXT,
                precio_ofertado REAL,
                precio_contraoferta REAL,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
        """)
    conn.commit()


def _quote_col(c: str) -> str:
    return f'"{c}"' if not c.isidentifier() or c[0].isdigit() else c


def _tabla_vacia(conn, tabla: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {tabla}")
        return cur.fetchone()[0] == 0


def _insert_seed_proveedores(conn: psycopg2.extensions.connection) -> int:
    proveedores = [
        ("Distribuidora Santiago Ltda.", "76.123.456-7", "ventas@dsantiago.cl", 85, "Cumplimiento historico: 95% entregas a tiempo"),
        ("Insumos Industriales Chile SPA", "77.234.567-8", "contacto@iichile.cl", 72, "Cumplimiento historico: 88% entregas a tiempo"),
        ("Proveedora Nacional del Sur", "78.345.678-9", "info@prosur.cl", 90, "Cumplimiento historico: 97% entregas a tiempo"),
        ("Comercial del Pacífico Ltda.", "79.456.789-0", "ventas@compac.cl", 65, "Cumplimiento historico: 82% entregas a tiempo"),
        ("Suministros Tecnologicos SPA", "80.567.890-1", "ventas@sutech.cl", 88, "Cumplimiento historico: 93% entregas a tiempo"),
        ("Logistica y Abastecimiento SA", "81.678.901-2", "ops@logabastece.cl", 78, "Cumplimiento historico: 90% entregas a tiempo"),
        ("Materiales de Construccion RML", "82.789.012-3", "pedidos@rmlconst.cl", 82, "Cumplimiento historico: 91% entregas a tiempo"),
        ("Oficina Total Express Ltda.", "83.890.123-4", "ventas@oficinatotal.cl", 70, "Cumplimiento historico: 85% entregas a tiempo"),
    ]
    for nombre, rut, email, score, historial in proveedores:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO proveedores (nombre, rut, email, reputacion_score, historial_cumplimiento)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (rut) DO NOTHING
            """, (nombre, rut, email, score, historial))
    conn.commit()
    return len(proveedores)


def _insert_seed_solicitudes(conn: psycopg2.extensions.connection) -> int:
    solicitudes = [
        ("Laptops empresariales", 15, 22500000, "alta"),
        ("Resmas de papel carta", 200, 1200000, "baja"),
        ("Toner para impresora HP", 30, 4500000, "media"),
        ("Sillas ergonomicas", 25, 12500000, "media"),
        ("Servidor NAS 12TB", 3, 4200000, "alta"),
        ("Escritorios modulares", 20, 14000000, "baja"),
        ("Licencias Microsoft 365", 50, 7500000, "alta"),
        ("Cables de red CAT6", 500, 2500000, "media"),
        ("Monitores 27 pulgadas", 30, 18000000, "media"),
        ("Extinguidores ABC 10kg", 12, 960000, "baja"),
    ]
    for producto, cantidad, presupuesto, urgencia in solicitudes:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO solicitudes (producto, cantidad, presupuesto_max, urgencia, estado)
                VALUES (%s, %s, %s, %s, 'pendiente')
            """, (producto, cantidad, presupuesto, urgencia))
    conn.commit()
    return len(solicitudes)


def _insert_seed_cotizaciones(conn: psycopg2.extensions.connection) -> int:
    ahora = datetime.now()
    cotizaciones = [
        (1, 1, 21000000, 15, 12, 15),
        (1, 5, 19500000, 10, 24, 8),
        (1, 3, 22800000, 20, 18, 25),
        (2, 1, 1100000, 3, 0, 5),
        (2, 4, 980000, 5, 0, 10),
        (2, 8, 1250000, 2, 0, 20),
        (3, 5, 4200000, 7, 6, 10),
        (3, 2, 4650000, 10, 12, 30),
        (3, 8, 3980000, 5, 6, 5),
        (4, 7, 11800000, 25, 24, 12),
        (4, 3, 13200000, 30, 36, 20),
        (4, 6, 12500000, 20, 24, 8),
        (5, 5, 3900000, 7, 36, 5),
        (5, 2, 4500000, 14, 24, 35),
        (6, 3, 13500000, 35, 12, 15),
        (6, 7, 12800000, 28, 24, 10),
        (6, 6, 14200000, 40, 12, 18),
        (7, 5, 7200000, 2, 12, 5),
        (7, 1, 7600000, 5, 12, 12),
        (7, 8, 6900000, 3, 6, 8),
        (8, 4, 2300000, 4, 0, 10),
        (8, 1, 2100000, 7, 0, 15),
        (9, 5, 16500000, 10, 24, 8),
        (9, 3, 19200000, 15, 36, 20),
        (9, 2, 17500000, 12, 12, 15),
        (10, 4, 880000, 5, 12, 10),
        (10, 6, 1020000, 7, 24, 18),
        (10, 7, 960000, 3, 12, 5),
    ]
    for solicitud_id, proveedor_id, precio, plazo, garantia, risk in cotizaciones:
        ts = ahora - timedelta(hours=2, minutes=len(cotizaciones))
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO cotizaciones (solicitud_id, proveedor_id, precio_total, plazo_dias, garantia_meses, risk_score, estado, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, 'recibida', %s)
            """, (solicitud_id, proveedor_id, precio, plazo, garantia, risk, ts))
    conn.commit()
    return len(cotizaciones)


def _insert_seed_negociaciones(conn: psycopg2.extensions.connection) -> int:
    ahora = datetime.now()
    negociaciones = [
        (1, 1, "cord_santiago@dsantiago.cl", "compras@nexora.cl", 21000000, 20000000),
        (1, 2, "cord_santiago@dsantiago.cl", "compras@nexora.cl", 20000000, 19500000),
        (4, 1, "ventas@oficinatotal.cl", "compras@nexora.cl", 1250000, 1150000),
        (4, 2, "ventas@oficinatotal.cl", "compras@nexora.cl", 1150000, 1100000),
        (7, 1, "ventas@sutech.cl", "compras@nexora.cl", 7200000, 7000000),
        (7, 2, "ventas@dsantiago.cl", "compras@nexora.cl", 7600000, 7400000),
        (10, 1, "ventas@compac.cl", "compras@nexora.cl", 880000, 850000),
        (10, 2, "ventas@compac.cl", "compras@nexora.cl", 850000, 830000),
        (13, 1, "ventas@sutech.cl", "compras@nexora.cl", 3900000, 3750000),
        (13, 2, "contacto@iichile.cl", "compras@nexora.cl", 4500000, 4300000),
        (19, 1, "ventas@sutech.cl", "compras@nexora.cl", 7200000, 7050000),
        (19, 2, "ventas@dsantiago.cl", "compras@nexora.cl", 7600000, 7500000),
        (23, 1, "ventas@sutech.cl", "compras@nexora.cl", 16500000, 15800000),
        (23, 2, "info@prosur.cl", "compras@nexora.cl", 19200000, 18500000),
        (28, 1, "pedidos@rmlconst.cl", "compras@nexora.cl", 960000, 940000),
    ]
    for cotizacion_id, ronda, email_env, email_rec, ofertado, contra in negociaciones:
        ts = ahora - timedelta(minutes=30 * ronda)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO negociaciones (cotizacion_id, ronda, email_enviado, email_recibido, precio_ofertado, precio_contraoferta, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (cotizacion_id, ronda, email_env, email_rec, ofertado, contra, ts))
    conn.commit()
    return len(negociaciones)


def _actualizar_mejores_cotizaciones(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE solicitudes s
            SET
                proveedor_elegido_id = mejor.proveedor_id,
                ahorro_conseguido = ROUND(((s.presupuesto_max - mejor.precio_total) / s.presupuesto_max * 100)::numeric, 2)
            FROM (
                SELECT DISTINCT ON (c.solicitud_id)
                    c.solicitud_id,
                    c.proveedor_id,
                    c.precio_total
                FROM cotizaciones c
                ORDER BY c.solicitud_id, c.precio_total ASC
            ) mejor
            WHERE mejor.solicitud_id = s.id
        """)
    conn.commit()


def _actualizar_estados(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE solicitudes
            SET estado = 'completada'
            WHERE proveedor_elegido_id IS NOT NULL AND estado = 'pendiente'
        """)
    conn.commit()


def ejecutar_carga(almacen_datos: dict) -> dict:
    t0 = time.perf_counter()
    logger.info("=" * 60)
    logger.info("Etapa de CARGA Neon (PostgreSQL) · NegocIA · inicio")

    conn = obtener_conexion_neon()
    _crear_tablas(conn)

    total_filas = 0
    resumen = {}

    if _tabla_vacia(conn, "proveedores"):
        f = _insert_seed_proveedores(conn)
        total_filas += f
        resumen["proveedores"] = f
        logger.info(f"Tabla proveedores -> {f} filas insertadas")
    else:
        logger.info("Tabla proveedores ya contiene datos, se omite seed")

    if _tabla_vacia(conn, "solicitudes"):
        f = _insert_seed_solicitudes(conn)
        total_filas += f
        resumen["solicitudes"] = f
        logger.info(f"Tabla solicitudes -> {f} filas insertadas")
    else:
        logger.info("Tabla solicitudes ya contiene datos, se omite seed")

    if _tabla_vacia(conn, "cotizaciones"):
        f = _insert_seed_cotizaciones(conn)
        total_filas += f
        resumen["cotizaciones"] = f
        logger.info(f"Tabla cotizaciones -> {f} filas insertadas")
    else:
        logger.info("Tabla cotizaciones ya contiene datos, se omite seed")

    if _tabla_vacia(conn, "negociaciones"):
        f = _insert_seed_negociaciones(conn)
        total_filas += f
        resumen["negociaciones"] = f
        logger.info(f"Tabla negociaciones -> {f} filas insertadas")
    else:
        logger.info("Tabla negociaciones ya contiene datos, se omite seed")

    _actualizar_mejores_cotizaciones(conn)
    _actualizar_estados(conn)

    conn.close()

    dur = time.perf_counter() - t0
    almacen_datos["Resumen_Carga"] = {
        "total_filas_insertadas": total_filas,
        "detalle_tablas": resumen,
        "duracion_s": round(dur, 3),
        "db_type": "Neon (PostgreSQL) · NegocIA",
    }
    logger.info(f"Total filas insertadas en todas las tablas: {total_filas}")
    logger.info(f"Base de datos: Neon (PostgreSQL) · NegocIA")
    logger.info(f"Etapa de CARGA Neon · fin ({dur:.3f}s)")
    logger.info("=" * 60)

    return almacen_datos
