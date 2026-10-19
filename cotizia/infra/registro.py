"""Registro anonimizado de consultas. Un solo contrato (`guardar`) y varios almacenes intercambiables.

COTIZIA_STORAGE = csv (por defecto) | sqlite | firestore | memoria
En Cloud Run el disco es efímero: para producción usa firestore.
"""
from __future__ import annotations

import csv
import os
import sqlite3
import threading
from pathlib import Path
from typing import Protocol

from config import DATA_DIR

CAMPOS = [
    "id_consulta", "id_sesion", "fecha_hora", "mensaje_anonimizado", "intencion_detectada",
    "regla_disparada", "producto", "cantidad", "total", "derivada", "etiqueta_revisada",
]


class Registro(Protocol):
    def guardar(self, fila: dict) -> None: ...


def _segura(valor) -> str:
    """Evita inyección de fórmulas si alguien abre el CSV en Excel."""
    s = str(valor)
    if s[:1] in ("=", "+", "@") or (s[:1] == "-" and not s[1:2].isdigit()):
        return "'" + s
    return s


class RegistroCSV:
    def __init__(self, ruta: str | Path):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def guardar(self, fila: dict) -> None:
        with self._lock:
            nuevo = not self.ruta.exists() or self.ruta.stat().st_size == 0
            with self.ruta.open("a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=CAMPOS)
                if nuevo:
                    w.writeheader()
                w.writerow({k: _segura(fila.get(k, "")) for k in CAMPOS})


class RegistroSQLite:
    def __init__(self, ruta: str | Path):
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(ruta), check_same_thread=False)
        self._lock = threading.Lock()
        self._con.execute(f"CREATE TABLE IF NOT EXISTS consultas ({', '.join(c + ' TEXT' for c in CAMPOS)})")

    def guardar(self, fila: dict) -> None:
        with self._lock:
            self._con.execute(
                f"INSERT INTO consultas VALUES ({', '.join('?' * len(CAMPOS))})",
                [str(fila.get(k, "")) for k in CAMPOS],
            )
            self._con.commit()


class RegistroFirestore:
    """Recomendado en Google Cloud: sin servidor, escala solo y no depende del disco de la instancia."""

    def __init__(self, coleccion: str = "consultas"):
        from google.cloud import firestore  # import perezoso

        self._col = firestore.Client().collection(coleccion)

    def guardar(self, fila: dict) -> None:
        self._col.add({k: fila.get(k, "") for k in CAMPOS})


class RegistroMemoria:
    """Para pruebas y demos."""

    def __init__(self):
        self.filas: list[dict] = []

    def guardar(self, fila: dict) -> None:
        self.filas.append(dict(fila))


def crear_registro() -> Registro:
    modo = os.getenv("COTIZIA_STORAGE", "csv").lower()
    if modo == "firestore":
        return RegistroFirestore(os.getenv("COTIZIA_FIRESTORE_COLLECTION", "consultas"))
    if modo == "sqlite":
        return RegistroSQLite(os.getenv("COTIZIA_SQLITE_PATH", DATA_DIR / "consultas.db"))
    if modo == "memoria":
        return RegistroMemoria()
    return RegistroCSV(os.getenv("COTIZIA_CSV_PATH", DATA_DIR / "consultas.csv"))
