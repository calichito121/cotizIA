"""Estructuras de datos: estado de la conversación, hechos del turno, reglas y respuesta."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from .catalogo import Catalogo, Producto
from .cotizador import Cotizacion, Item
from .utilidades import contiene, extraer_cantidad, normalizar
from .vocabulario import INTENCIONES_COTIZACION, PALABRAS_CLAVE


@dataclass
class Conversacion:
    """Estado que persiste entre turnos (se guarda en la sesión del usuario, no en el servidor)."""
    id_sesion: str = field(default_factory=lambda: uuid.uuid4().hex[:12])  # seudónimo
    estado: str = "idle"  # idle | esperando_producto | esperando_cantidad | cotizado
    items: list[Item] = field(default_factory=list)
    producto_pendiente: Optional[Producto] = None
    cantidad_pendiente: Optional[int] = None
    entrega_solicitada: bool = False
    fuera_dominio_seguidas: int = 0
    aviso_dado: bool = False

    def reiniciar_flujo(self) -> None:
        self.estado = "idle"
        self.items.clear()
        self.producto_pendiente = None
        self.cantidad_pendiente = None
        self.entrega_solicitada = False


@dataclass
class Hechos:
    """Memoria de trabajo de UN turno: lo que las reglas leen y escriben."""
    conv: Conversacion
    catalogo: Catalogo
    texto: str  # ya sin datos personales después de R25
    norm: str = ""
    intencion: Optional[str] = None
    confianza: Optional[float] = None
    lineas: list[tuple[Producto, int]] = field(default_factory=list)  # pares (producto, cantidad)
    producto: Optional[Producto] = None  # producto sin cantidad
    cantidad: Optional[int] = None  # cantidad sin producto
    entrega: bool = False
    recalcular: bool = False
    cotizacion: Optional[Cotizacion] = None
    partes: list[str] = field(default_factory=list)
    derivar: bool = False
    traza: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.refrescar()

    def refrescar(self) -> None:
        """Extrae producto, cantidad y envío del texto (+ datos pendientes si hay flujo en curso)."""
        self.norm = normalizar(self.texto)
        lineas = self.catalogo.extraer_pares(self.norm)
        prod = cant = None
        if not lineas:
            prod = self.catalogo.buscar(self.norm)
            cant = extraer_cantidad(self.norm)
            if self.conv.estado != "idle":
                prod = prod or self.conv.producto_pendiente
                cant = cant if cant is not None else self.conv.cantidad_pendiente
            if prod is not None and cant is not None:
                lineas, prod, cant = [(prod, cant)], None, None
        self.lineas, self.producto, self.cantidad = lineas, prod, cant
        self.entrega = contiene(self.norm, PALABRAS_CLAVE["entrega"])

    @property
    def cotizando(self) -> bool:
        return self.intencion in INTENCIONES_COTIZACION or (self.intencion is None and self.conv.estado != "idle")


@dataclass(frozen=True)
class Regla:
    id: str
    descripcion: str
    prioridad: int  # mayor = más específica, se dispara primero
    condicion: Callable[[Hechos], bool]
    accion: Callable[[Hechos], None]
    orden: int = 0  # desempate: menor número primero


@dataclass(frozen=True)
class Respuesta:
    texto: str
    intencion: str
    traza: tuple[str, ...]
    derivar: bool
    cotizacion: Optional[Cotizacion]
    mensaje_anonimizado: str
    whatsapp_url: Optional[str]
    mailto_url: Optional[str]
    ms: float
