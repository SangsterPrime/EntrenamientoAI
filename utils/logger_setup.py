"""
Utilidad compartida de logging estructurado para todo el pipeline.
Formato obligatorio: [YYYY-MM-DD HH:MM:SS] - [NIVEL] - [modulo.funcion] → mensaje
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
DIR_LOGS = RAIZ / "IA_Proyecto" / "logs"
DIR_LOGS.mkdir(parents=True, exist_ok=True)


def configurar_logger(
    nombre: str,
    archivo: str | None = None,
    nivel: int = logging.INFO,
    consola: bool = True,
) -> logging.Logger:
    logger = logging.getLogger(nombre)
    logger.setLevel(nivel)
    logger.handlers.clear()

    _fmt = "[%(asctime)s] - [%(levelname)s] - [%(name)s] -> %(message)s"
    _datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(_fmt, datefmt=_datefmt)

    if archivo:
        fh = logging.FileHandler(DIR_LOGS / archivo, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    if consola:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger
