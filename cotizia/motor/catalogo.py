"""Catálogo de productos y extracción de (producto, cantidad) desde el texto."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .utilidades import normalizar


@dataclass(frozen=True)
class Producto:
    sku: str
    nombre: str
    precio: Decimal  # precio unitario SIN IGV
    alias: tuple[str, ...] = ()


class Catalogo:
    def __init__(self, productos: list[Producto]):
        if not productos:
            raise ValueError("El catálogo está vacío.")
        self.productos = list(productos)
        self._por_alias: dict[str, Producto] = {}
        for p in self.productos:
            for alias in {normalizar(p.nombre), *(normalizar(a) for a in p.alias)}:
                if alias:
                    self._por_alias[alias] = p
        alt = "|".join(re.escape(a) for a in sorted(self._por_alias, key=len, reverse=True))
        self._re_alias = re.compile(rf"(?<!\w)({alt})(?!\w)")
        # "20 unidades de producto basico", "60 productos premium", "5 de premium", "-5 basico"
        self._re_par = re.compile(
            rf"(?<![\w.])(-?\d+)\s*(?:unidades|unidad|uds?\.?|u)?\s*(?:de\s+)?(?:productos?\s+)?({alt})(?!\w)"
        )

    @classmethod
    def desde_csv(cls, ruta: Path) -> "Catalogo":
        with open(ruta, newline="", encoding="utf-8") as f:
            filas = list(csv.DictReader(f))
        return cls([
            Producto(
                sku=r["sku"].strip(),
                nombre=r["nombre"].strip(),
                precio=Decimal(r["precio_unitario"].strip()),
                alias=tuple(a for a in r.get("alias", "").split("|") if a.strip()),
            )
            for r in filas
        ])

    def buscar(self, norm: str) -> Producto | None:
        m = self._re_alias.search(norm)
        return self._por_alias[m.group(1)] if m else None

    def extraer_pares(self, norm: str) -> list[tuple[Producto, int]]:
        return [(self._por_alias[m.group(2)], int(m.group(1))) for m in self._re_par.finditer(norm)]
