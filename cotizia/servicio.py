"""Capa de servicio: une motor + registro. La interfaz (Streamlit hoy, API REST mañana) solo habla con esto."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from config import DATA_DIR, Negocio, cargar_negocio
from infra.registro import Registro, crear_registro
from motor import Catalogo, Conversacion, MotorInferencia, Respuesta

log = logging.getLogger("cotizia")


def nueva_fila(resp: Respuesta, id_sesion: str) -> dict:
    lineas = resp.cotizacion.lineas if resp.cotizacion else ()
    return {
        "id_consulta": uuid.uuid4().hex[:12],
        "id_sesion": id_sesion,
        "fecha_hora": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mensaje_anonimizado": resp.mensaje_anonimizado,
        "intencion_detectada": resp.intencion,
        "regla_disparada": ",".join(resp.traza),
        "producto": "|".join(l.nombre for l in lineas),
        "cantidad": "|".join(str(l.cantidad) for l in lineas),
        "total": str(resp.cotizacion.total) if resp.cotizacion else "",
        "derivada": str(resp.derivar).lower(),
        "etiqueta_revisada": "",  # se completa a mano: es la etiqueta para entrenar en la semana 16
    }


class Asistente:
    def __init__(self, motor: MotorInferencia, registro: Registro, negocio: Negocio):
        self.motor, self.registro, self.negocio = motor, registro, negocio

    def nueva_conversacion(self) -> Conversacion:
        return Conversacion()

    def bienvenida(self, conv: Conversacion) -> str:
        return self.motor.bienvenida(conv)

    def atender(self, mensaje: str, conv: Conversacion) -> Respuesta:
        resp = self.motor.responder(mensaje, conv)
        try:
            self.registro.guardar(nueva_fila(resp, conv.id_sesion))
        except Exception:  # el chat nunca debe caerse por culpa del registro
            log.exception("No se pudo guardar la consulta")
        return resp


def crear_asistente() -> Asistente:
    negocio = cargar_negocio()
    catalogo = Catalogo.desde_csv(DATA_DIR / "catalogo.csv")
    clasificador = None
    ruta_modelo = os.getenv("COTIZIA_MODELO_ML")  # semana 16: ruta al .joblib
    if ruta_modelo:
        from motor.clasificadores import ClasificadorML

        clasificador = ClasificadorML(ruta_modelo)
    return Asistente(MotorInferencia(catalogo, negocio, clasificador), crear_registro(), negocio)
