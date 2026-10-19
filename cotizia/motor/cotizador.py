"""Cálculo determinista del presupuesto (Decimal, nunca float)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from config import Negocio

from .catalogo import Producto
from .utilidades import soles

_CENT = Decimal("0.01")


def redondear(x: Decimal) -> Decimal:
    return x.quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass
class Item:
    producto: Producto
    cantidad: int
    descuento_pct: Optional[Decimal] = None  # lo asignan las reglas R17 a R19


@dataclass(frozen=True)
class LineaCotizacion:
    nombre: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    descuento_pct: Decimal
    descuento: Decimal


@dataclass(frozen=True)
class Cotizacion:
    lineas: tuple[LineaCotizacion, ...]
    subtotal: Decimal
    descuento: Decimal
    envio: Decimal
    base_imponible: Decimal
    igv: Decimal
    total: Decimal
    vigencia_dias: int


def calcular(items: list[Item], negocio: Negocio, con_envio: bool) -> Cotizacion:
    lineas = []
    for it in items:
        sub = redondear(it.producto.precio * it.cantidad)
        pct = it.descuento_pct or Decimal("0")
        lineas.append(LineaCotizacion(it.producto.nombre, it.cantidad, it.producto.precio, sub, pct, redondear(sub * pct)))
    cero = Decimal("0.00")
    subtotal = sum((l.subtotal for l in lineas), cero)
    descuento = sum((l.descuento for l in lineas), cero)
    envio = negocio.costo_envio if con_envio else cero
    base = subtotal - descuento + envio
    igv = redondear(base * negocio.igv)
    return Cotizacion(tuple(lineas), subtotal, descuento, envio, base, igv, base + igv, negocio.vigencia_dias)


def formatear_markdown(cot: Cotizacion, negocio: Negocio, ofrecer_envio: bool) -> str:
    filas = ["| Producto | Cant. | P. unit. | Subtotal |", "|---|---:|---:|---:|"]
    filas += [f"| {l.nombre} | {l.cantidad} | {soles(l.precio_unitario)} | {soles(l.subtotal)} |" for l in cot.lineas]
    detalle = [f"- Subtotal: {soles(cot.subtotal)}"]
    if cot.descuento:
        detalle.append(f"- Descuento por cantidad: −{soles(cot.descuento)}")
    if cot.envio:
        detalle.append(f"- Envío a domicilio: {soles(cot.envio)}")
    detalle += [f"- IGV ({negocio.igv * 100:.0f} %): {soles(cot.igv)}", f"- **Total: {soles(cot.total)}**"]
    pie = f"_Monto estimado, vigente por {cot.vigencia_dias} días. La validación final la realiza el negocio._"
    pregunta = "¿Deseas agregar otro producto" + (", incluir envío a domicilio" if ofrecer_envio else "") + " o enviar tu pedido?"
    return "**Presupuesto estimado**\n\n" + "\n".join(filas) + "\n\n" + "\n".join(detalle) + "\n\n" + pie + "\n\n" + pregunta


def resumen_texto(cot: Cotizacion) -> str:
    partes = ", ".join(f"{l.cantidad} x {l.nombre}" for l in cot.lineas)
    envio = " con envío" if cot.envio else ""
    return f"Presupuesto estimado: {partes}{envio}. Total {soles(cot.total)} (incluye IGV)."
