"""Casos de prueba del avance (semana 8) y reporte de resultados.

    python -m tests.casos_prueba      -> imprime la tabla de la sección 6 del documento
    pytest                            -> corre las mismas comprobaciones como pruebas
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

from config import DATA_DIR, cargar_negocio
from infra.registro import RegistroMemoria
from motor import Catalogo, MotorInferencia
from motor.clasificadores import LineaBasePalabrasClave
from servicio import Asistente


@dataclass(frozen=True)
class Caso:
    id: str
    mensajes: tuple[str, ...]  # el resultado se evalúa sobre el ÚLTIMO mensaje
    intencion: str
    reglas: tuple[str, ...]  # reglas que deben aparecer en la traza
    derivar: bool = False
    total: Decimal | None = None


CASOS = (
    Caso("C01", ("Hola, buenas tardes",), "saludo", ("R1", "R26")),
    Caso("C02", ("¿A qué hora atienden?",), "horario", ("R2",)),
    Caso("C03", ("¿Cuánto cuesta el producto estándar?",), "precios", ("R4",)),
    Caso("C04", ("Quiero cotizar 20 unidades de producto básico",), "cotizar",
         ("R6", "R16", "R17", "R21", "R22"), total=Decimal("1121.00")),
    Caso("C05", ("Necesito presupuesto de 60 productos premium con delivery",), "cotizar",
         ("R6", "R16", "R18", "R20", "R21", "R22", "R23"), derivar=True, total=Decimal("7658.20")),
    Caso("C06", ("Cotizar 9 unidades de producto básico",), "cotizar",
         ("R6", "R16", "R21", "R22"), total=Decimal("531.00")),
    Caso("C07", ("Cotizar 50 unidades de producto estándar",), "cotizar",
         ("R6", "R16", "R18", "R21", "R22"), total=Decimal("4248.00")),
    Caso("C08", ("Cotizar -5 unidades de producto básico",), "cotizar", ("R6", "R15")),
    Caso("C09", ("¿Aceptan Yape?",), "medios_pago", ("R8",)),
    Caso("C10", ("Quiero hablar con un asesor",), "derivar", ("R10",), derivar=True),
    Caso("C11", ("¿Cuál es la capital de Francia?", "¿Cuál es la capital de Francia?"),
         "fuera_de_dominio", ("R12", "R24"), derivar=True),
    Caso("C12", ("Mi cel es 987654321, quiero cotizar",), "cotizar", ("R25", "R6", "R13")),
)


def crear_asistente_de_prueba() -> Asistente:
    negocio = cargar_negocio()
    catalogo = Catalogo.desde_csv(DATA_DIR / "catalogo.csv")
    return Asistente(MotorInferencia(catalogo, negocio), RegistroMemoria(), negocio)


@dataclass
class Resultado:
    caso: Caso
    resp: object
    filas: list
    base_intencion: str


@lru_cache(maxsize=1)
def ejecutar_todos() -> tuple[Resultado, ...]:
    base = LineaBasePalabrasClave()
    salida = []
    for caso in CASOS:
        asistente = crear_asistente_de_prueba()  # conversación nueva por caso
        conv = asistente.nueva_conversacion()
        resp = None
        for msg in caso.mensajes:
            resp = asistente.atender(msg, conv)
        salida.append(Resultado(caso, resp, asistente.registro.filas, base.predecir(caso.mensajes[-1])))
    return tuple(salida)


# ---------------- pruebas (pytest) ----------------
def test_intenciones():
    for r in ejecutar_todos():
        assert r.resp.intencion == r.caso.intencion, f"{r.caso.id}: {r.resp.intencion}"


def test_reglas_esperadas_en_la_traza():
    for r in ejecutar_todos():
        faltan = set(r.caso.reglas) - set(r.resp.traza)
        assert not faltan, f"{r.caso.id}: faltan {faltan}; traza={r.resp.traza}"


def test_montos_exactos():
    for r in ejecutar_todos():
        if r.caso.total is not None:
            assert r.resp.cotizacion is not None and r.resp.cotizacion.total == r.caso.total, r.caso.id


def test_derivaciones():
    for r in ejecutar_todos():
        assert r.resp.derivar == r.caso.derivar, r.caso.id


def test_privacidad_en_el_registro():
    r = next(x for x in ejecutar_todos() if x.caso.id == "C12")
    guardado = " ".join(f["mensaje_anonimizado"] for f in r.filas)
    assert "987654321" not in guardado and "[TELEFONO]" in guardado


# ---------------- reporte (sección 6 del documento) ----------------
def reporte() -> str:
    rs = ejecutar_todos()
    n = len(rs)
    pct = lambda a, b: f"{a}/{b} ({100 * a / b:.0f} %)"

    int_exp = sum(r.resp.intencion == r.caso.intencion for r in rs)
    int_base = sum(r.base_intencion == r.caso.intencion for r in rs)
    con_monto = [r for r in rs if r.caso.total is not None]
    mon_exp = sum(r.resp.cotizacion is not None and r.resp.cotizacion.total == r.caso.total for r in con_monto)
    con_der = [r for r in rs if r.caso.derivar]
    der_exp = sum(r.resp.derivar for r in con_der)
    der_base = sum(r.base_intencion == "derivar" for r in con_der)
    c12 = next(r for r in rs if r.caso.id == "C12")
    priv_exp = "987654321" not in " ".join(f["mensaje_anonimizado"] for f in c12.filas)
    ms = statistics.mean(r.resp.ms for r in rs)

    lineas = [
        "| Métrica | Meta | Línea base A (palabras clave) | Sistema experto B |",
        "|---|---|---|---|",
        f"| Casos con intención correcta (de {n}) | ≥ 80 % | {pct(int_base, n)} | {pct(int_exp, n)} |",
        f"| Cotizaciones con monto exacto (C04–C07) | 100 % | {pct(0, len(con_monto))} (no calcula) | {pct(mon_exp, len(con_monto))} |",
        f"| Derivaciones correctas (C05, C10, C11) | 100 % | {pct(der_base, len(con_der))} | {pct(der_exp, len(con_der))} |",
        f"| Datos personales enmascarados (C12) | 100 % | 0/1 (no anonimiza) | {pct(int(priv_exp), 1)} |",
        f"| Tiempo medio de respuesta | < 2 s | — | {ms:.2f} ms |",
        "",
        "Detalle por caso:",
        "",
        "| Caso | Intención A | Intención B | Reglas disparadas (B) |",
        "|---|---|---|---|",
    ]
    lineas += [f"| {r.caso.id} | {r.base_intencion} | {r.resp.intencion} | {' → '.join(r.resp.traza)} |" for r in rs]
    return "\n".join(lineas)


if __name__ == "__main__":
    print(reporte())
