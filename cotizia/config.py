"""Configuración central.

Todo lo que cambia por cliente o rubro vive en data/ (catalogo.csv y negocio.json) o en
variables de entorno. El código del motor no se toca al cambiar de rubro.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("COTIZIA_DATA_DIR", BASE_DIR / "data"))


@dataclass(frozen=True)
class Negocio:
    nombre: str
    igv: Decimal
    costo_envio: Decimal
    vigencia_dias: int
    umbral_derivacion: Decimal
    cantidad_maxima: int
    descuentos: tuple[tuple[int, Decimal], ...]  # (cantidad mínima, porcentaje), ascendente
    whatsapp: str
    correo: str
    faq: dict[str, str]


def cargar_negocio(ruta: Path | None = None) -> Negocio:
    ruta = Path(ruta) if ruta else DATA_DIR / "negocio.json"
    d = json.loads(ruta.read_text(encoding="utf-8"), parse_float=Decimal)
    tramos = tuple(sorted((int(t["desde"]), Decimal(str(t["pct"]))) for t in d["descuentos"]))
    if len(tramos) > 3:
        raise ValueError("Máximo 3 tramos de descuento (reglas R17 a R19).")
    return Negocio(
        nombre=d["nombre"],
        igv=Decimal(str(d["igv"])),
        costo_envio=Decimal(str(d["costo_envio"])),
        vigencia_dias=int(d["vigencia_dias"]),
        umbral_derivacion=Decimal(str(d["umbral_derivacion"])),
        cantidad_maxima=int(d["cantidad_maxima"]),
        descuentos=tramos,
        whatsapp=os.getenv("COTIZIA_WHATSAPP", d["whatsapp"]),
        correo=os.getenv("COTIZIA_CORREO", d["correo"]),
        faq=d["faq"],
    )
