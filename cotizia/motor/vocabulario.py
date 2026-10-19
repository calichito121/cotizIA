"""Vocabulario del dominio (ya normalizado: minúsculas y sin tildes).

Es la única fuente de palabras clave: la usan las reglas R1 a R11 y la línea base.
"""
from __future__ import annotations

FUERA_DE_DOMINIO = "fuera_de_dominio"
INTENCIONES_COTIZACION = ("cotizar", "pedido")

PALABRAS_CLAVE: dict[str, tuple[str, ...]] = {
    "saludo": ("hola", "buenas", "buenos dias", "buen dia"),
    "horario": ("horario", "horarios", "atienden", "a que hora", "hora de atencion", "abierto", "abren", "cierran"),
    "ubicacion": ("donde", "ubicacion", "direccion", "local", "ubicados"),
    "precios": ("precio", "precios", "cuanto cuesta", "cuanto sale", "cuanto vale", "costo", "tarifa"),
    "catalogo": ("catalogo", "productos", "que venden", "que ofrecen", "servicios"),
    "cotizar": ("cotizar", "cotizacion", "cotiza", "presupuesto", "proforma"),
    "pedido": ("pedido", "comprar", "quiero pedir", "pedir", "ordenar"),
    "medios_pago": ("pago", "pagos", "pagar", "yape", "plin", "transferencia", "tarjeta", "efectivo"),
    "entrega": ("entrega", "entregas", "envio", "envios", "delivery", "despacho", "domicilio"),
    "derivar": ("asesor", "asesora", "persona", "hablar con", "humano", "agente"),
    "cierre": ("gracias", "chau", "adios", "hasta luego"),
}

# Palabras que, dentro de una cotización en curso, indican "agrega el envío".
VERBOS_AGREGAR = ("con", "agrega", "agregar", "anade", "anadir", "incluye", "incluir", "si", "quiero", "necesito")
