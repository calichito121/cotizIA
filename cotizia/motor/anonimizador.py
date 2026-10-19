"""R25: enmascara datos personales ANTES de registrar el mensaje (Ley N.° 29733)."""
from __future__ import annotations

import re

_PATRONES = (
    ("[CORREO]", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("[TELEFONO]", re.compile(r"(?<!\d)(?:\+?51[\s-]?)?9\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)")),
    ("[DNI]", re.compile(r"(?<!\d)\d{8}(?!\d)")),
)


def anonimizar(texto: str) -> tuple[str, list[str]]:
    """Devuelve (texto enmascarado, tipos de dato detectados)."""
    tipos: list[str] = []
    for etiqueta, patron in _PATRONES:
        texto, n = patron.subn(etiqueta, texto)
        if n:
            tipos.append(etiqueta.strip("[]").lower())
    return texto, tipos
