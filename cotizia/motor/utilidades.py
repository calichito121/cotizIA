"""Funciones de apoyo: normalización de texto, búsqueda de palabras y formato de dinero."""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios simples."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip()


def contiene(norm: str, claves) -> bool:
    """True si alguna palabra o frase de `claves` aparece completa en el texto normalizado."""
    return any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", norm) for k in claves)


_RE_CANTIDAD = re.compile(r"(?<![\w.])(-?\d+)(?!\w|[.,]\d)")


def extraer_cantidad(norm: str) -> int | None:
    m = _RE_CANTIDAD.search(norm)
    return int(m.group(1)) if m else None


def soles(monto: Decimal) -> str:
    return f"S/ {monto:,.2f}"
