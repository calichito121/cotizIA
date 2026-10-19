"""Motor de inferencia con encadenamiento hacia adelante.

Ciclo:  mientras existan reglas aplicables (condición verdadera y aún no disparadas en este turno),
dispara la de mayor prioridad (a igual prioridad, la definida primero), ejecuta su acción —que agrega
hechos o texto de respuesta— y registra su id en la traza. El motor NO guarda estado: todo el estado
vive en `Conversacion`, por eso se puede escalar horizontalmente (varias instancias en Cloud Run).
"""
from __future__ import annotations

import time
from urllib.parse import quote

from config import Negocio

from .catalogo import Catalogo
from .cotizador import resumen_texto
from .modelos import Conversacion, Hechos, Respuesta
from .reglas import construir_reglas
from .textos import AVISO_AUTOMATICO, SALUDO, SIN_REGLA

MAX_CARACTERES = 500


class MotorInferencia:
    def __init__(self, catalogo: Catalogo, negocio: Negocio, clasificador=None):
        self.catalogo = catalogo
        self.negocio = negocio
        self.reglas = construir_reglas(catalogo, negocio, clasificador)

    def bienvenida(self, conv: Conversacion) -> str:
        conv.aviso_dado = True
        return AVISO_AUTOMATICO + "\n\n" + SALUDO.format(nombre=self.negocio.nombre)

    def responder(self, mensaje: str, conv: Conversacion) -> Respuesta:
        t0 = time.perf_counter()
        h = Hechos(conv=conv, catalogo=self.catalogo, texto=mensaje.strip()[:MAX_CARACTERES])
        disparadas: set[str] = set()
        while True:
            candidatas = [r for r in self.reglas if r.id not in disparadas and r.condicion(h)]
            if not candidatas:
                break
            regla = max(candidatas, key=lambda r: (r.prioridad, -r.orden))
            disparadas.add(regla.id)
            h.traza.append(regla.id)
            regla.accion(h)

        if h.intencion != "fuera_de_dominio":
            conv.fuera_dominio_seguidas = 0
        if not h.partes:
            h.partes.append(SIN_REGLA)
            h.traza.append("SIN_REGLA")
        intencion = h.intencion or ("cotizar" if conv.estado != "idle" else "desconocida")
        wa, mail = self._enlaces(h) if (h.derivar or h.cotizacion) else (None, None)
        return Respuesta(
            texto="\n\n".join(h.partes), intencion=intencion, traza=tuple(h.traza), derivar=h.derivar,
            cotizacion=h.cotizacion, mensaje_anonimizado=h.texto, whatsapp_url=wa, mailto_url=mail,
            ms=(time.perf_counter() - t0) * 1000,
        )

    def _enlaces(self, h: Hechos) -> tuple[str, str]:
        detalle = resumen_texto(h.cotizacion) if h.cotizacion else f"Consulta: {h.texto}"
        cuerpo = f"Hola, escribo desde CotizIA. {detalle}"
        wa = f"https://wa.me/{self.negocio.whatsapp}?text={quote(cuerpo)}"
        mail = f"mailto:{self.negocio.correo}?subject={quote('Consulta desde CotizIA')}&body={quote(cuerpo)}"
        return wa, mail
