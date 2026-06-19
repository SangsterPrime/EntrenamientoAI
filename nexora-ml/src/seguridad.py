"""
NEXORA · Módulo de Seguridad y Protección de Datos
==================================================
seguridad.py — Utilidades de anonimización, enmascaramiento y control de
acceso aplicadas al dataset de clientes, en cumplimiento de la Ley 19.628 y
la Ley 21.719 (Chile).

Implementa, en código, las medidas descritas en la auditoría de seguridad:
    - Seudonimización de identificadores (hash con sal).
    - Generalización de datos personales (edad → rango etario).
    - Enmascaramiento para logs y vistas de roles no privilegiados.
    - Verificación de permisos por rol (RBAC mínimo).

Principio rector: minimización de datos — el modelo de IA NO requiere datos
identificatorios directos (RUT, nombre), sólo variables de comportamiento.
"""
from __future__ import annotations

import hashlib
import os

import pandas as pd

# Sal de seudonimización. En producción proviene de variable de entorno/secreto,
# nunca embebida en el código (ver .env / Docker secrets).
_SAL = os.getenv("NEXORA_SALT", "nexora-demo-salt")

# Columnas clasificadas como dato personal sensible (requieren protección).
COLUMNAS_SENSIBLES = ["edad"]

# Matriz de control de acceso basada en roles (RBAC).
# Define qué columnas puede ver cada rol que opera sobre la solución.
ROLES = {
    "admin":      {"ver_sensibles": True,  "ver_scoring": True,  "exportar": True},
    "analista":   {"ver_sensibles": False, "ver_scoring": True,  "exportar": True},
    "retencion":  {"ver_sensibles": False, "ver_scoring": True,  "exportar": False},
    "auditor":    {"ver_sensibles": False, "ver_scoring": False, "exportar": False},
}


def seudonimizar_id(valor: str | int) -> str:
    """Devuelve un seudónimo irreversible (SHA-256 + sal) de un identificador."""
    bruto = f"{_SAL}:{valor}".encode("utf-8")
    return hashlib.sha256(bruto).hexdigest()[:16]


def generalizar_edad(edad: int) -> str:
    """Generaliza la edad en rangos etarios (k-anonimato básico)."""
    if edad < 25:
        return "18-24"
    if edad < 35:
        return "25-34"
    if edad < 45:
        return "35-44"
    if edad < 55:
        return "45-54"
    if edad < 65:
        return "55-64"
    return "65+"


def enmascarar_para_rol(df: pd.DataFrame, rol: str) -> pd.DataFrame:
    """
    Devuelve una vista del DataFrame conforme a los permisos del rol:
    los roles sin 'ver_sensibles' reciben la edad generalizada y, sin
    'ver_scoring', no acceden a la probabilidad de abandono.
    """
    if rol not in ROLES:
        raise PermissionError(f"Rol desconocido: {rol}")
    permisos = ROLES[rol]
    vista = df.copy()

    if not permisos["ver_sensibles"] and "edad" in vista.columns:
        vista["edad"] = vista["edad"].apply(generalizar_edad)

    if not permisos["ver_scoring"]:
        vista = vista.drop(columns=[c for c in ("prob_abandono", "segmento_riesgo",
                                                "accion_retencion") if c in vista.columns])
    return vista


def puede_exportar(rol: str) -> bool:
    """Verifica si el rol tiene permiso de exportación de datos."""
    return ROLES.get(rol, {}).get("exportar", False)


if __name__ == "__main__":
    demo = pd.DataFrame({
        "cliente_id": [1001, 1002, 1003],
        "edad": [22, 47, 68],
        "reclamos": [4, 1, 0],
        "prob_abandono": [0.91, 0.30, 0.05],
        "segmento_riesgo": ["ALTO", "MEDIO", "BAJO"],
    })
    demo["cliente_id"] = demo["cliente_id"].apply(seudonimizar_id)

    print("=== Vista rol ADMIN (acceso total) ===")
    print(enmascarar_para_rol(demo, "admin").to_string(index=False))
    print("\n=== Vista rol RETENCION (edad generalizada, sin export) ===")
    print(enmascarar_para_rol(demo, "retencion").to_string(index=False))
    print(f"  ¿Puede exportar?: {puede_exportar('retencion')}")
    print("\n=== Vista rol AUDITOR (sin scoring ni sensibles) ===")
    print(enmascarar_para_rol(demo, "auditor").to_string(index=False))
