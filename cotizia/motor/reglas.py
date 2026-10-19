"""Base de reglas R1 a R26 (más la regla opcional ML de la semana 16).

Cada regla es: id, prioridad, condición(hechos) y acción(hechos). El motor las dispara por
encadenamiento hacia adelante (ver motor_inferencia.py).
"""
from __future__ import annotations

from decimal import Decimal

from config import Negocio

from .anonimizador import anonimizar
from .catalogo import Catalogo
from .cotizador import Item, calcular, formatear_markdown
from .modelos import Hechos, Regla
from .textos import AVISO_AUTOMATICO, FUERA_DE_DOMINIO as TXT_FUERA, SALUDO
from .utilidades import contiene, normalizar, soles
from .vocabulario import FUERA_DE_DOMINIO, INTENCIONES_COTIZACION, PALABRAS_CLAVE, VERBOS_AGREGAR


def construir_reglas(catalogo: Catalogo, negocio: Negocio, clasificador=None) -> list[Regla]:
    faq = {k: v.format(costo_envio=soles(negocio.costo_envio)) for k, v in negocio.faq.items()}
    igv_txt = f"{negocio.igv * 100:.0f}"
    ok = lambda c: 1 <= c <= negocio.cantidad_maxima  # cantidad válida
    reglas: list[Regla] = []

    def regla(id_: str, desc: str, prioridad: int, cond, accion) -> None:
        reglas.append(Regla(id_, desc, prioridad, cond, accion, orden=len(reglas)))

    # ---------- textos reutilizables ----------
    def lista_productos() -> str:
        return "\n".join(f"- {p.nombre}: {soles(p.precio)} por unidad" for p in catalogo.productos)

    def txt_descuentos() -> str:
        if not negocio.descuentos:
            return ""
        tramos = ", ".join(f"{pct * 100:.0f} % desde {desde} unidades" for desde, pct in negocio.descuentos)
        return f"Descuentos por cantidad: {tramos}."

    # ---------- acciones por intención (las usan R1 a R11 y la regla ML) ----------
    def a_saludo(h): h.partes.append(SALUDO.format(nombre=negocio.nombre))
    def a_horario(h): h.partes.append(faq["horario"])
    def a_ubicacion(h): h.partes.append(faq["ubicacion"])
    def a_medios_pago(h): h.partes.append(faq["medios_pago"])
    def a_entrega(h): h.partes.append(faq["entrega"])
    def a_cotizar(h): pass  # el flujo lo conducen R13 a R16
    def a_pedido(h): h.partes.append("¡Perfecto! Para registrar tu pedido armemos primero un presupuesto.")

    def a_catalogo(h):
        h.partes.append("Esto es lo que ofrecemos:\n" + lista_productos() +
                        f"\n\n_Precios sin IGV; el presupuesto añade IGV de {igv_txt} %._ ¿Quieres que te arme un presupuesto?")

    def a_precios(h):
        if h.producto is not None:
            p = h.producto
            h.partes.append(f"**{p.nombre}**: {soles(p.precio)} por unidad (sin IGV; el presupuesto añade IGV de {igv_txt} %). {txt_descuentos()}".strip())
        else:
            h.partes.append("Estos son nuestros precios (sin IGV):\n" + lista_productos() + f"\n\n{txt_descuentos()} ¿Quieres un presupuesto?")

    def a_derivar(h):
        h.derivar = True
        h.partes.append("Con gusto te comunico con una persona del negocio. Usa los botones de abajo (WhatsApp o correo).")

    def a_cierre(h):
        h.partes.append("¡Gracias por escribirnos! Cuando quieras otro presupuesto, aquí estaré 😊")
        h.conv.reiniciar_flujo()

    ACCIONES = {
        "saludo": a_saludo, "horario": a_horario, "ubicacion": a_ubicacion, "precios": a_precios,
        "catalogo": a_catalogo, "cotizar": a_cotizar, "pedido": a_pedido, "medios_pago": a_medios_pago,
        "entrega": a_entrega, "derivar": a_derivar, "cierre": a_cierre,
    }

    def fijar(h: Hechos, intencion: str) -> None:
        h.intencion = intencion
        ACCIONES[intencion](h)

    # ---------- reglas de entrada: privacidad y transparencia (R25, R26) ----------
    def a_anonimizar(h):
        h.texto, tipos = anonimizar(h.texto)
        h.refrescar()
        h.partes.append(f"🔒 Por tu privacidad no guardo datos personales: oculté tu {', '.join(tipos)} en el registro. No hace falta que los escribas aquí.")

    regla("R25", "Si el mensaje trae teléfono, DNI o correo → enmascararlo y avisar", 99,
          lambda h: anonimizar(h.texto)[0] != h.texto, a_anonimizar)

    def a_aviso(h):
        h.conv.aviso_dado = True
        h.partes.insert(0, AVISO_AUTOMATICO)

    regla("R26", "Si inicia la conversación → avisar que es un asistente automático", 98,
          lambda h: not h.conv.aviso_dado, a_aviso)

    # ---------- (semana 16) clasificador ML opcional; si no decide, caen las reglas de palabras ----------
    if clasificador is not None:
        def a_ml(h):
            etiqueta, prob = clasificador.predecir(h.norm)
            h.confianza = prob
            if etiqueta in ACCIONES:
                fijar(h, etiqueta)
        regla("ML", "Clasificador de intención entrenado (TF-IDF + NB/SVM)", 97, lambda h: h.intencion is None, a_ml)

    # ---------- R1 a R11: intención por palabras clave ----------
    def por_palabras(id_, intencion, prioridad, extra=None, claves=None):
        claves = claves or PALABRAS_CLAVE[intencion]
        def cond(h): return h.intencion is None and contiene(h.norm, claves) and (extra(h) if extra else True)
        regla(id_, f"Si contiene {', '.join(claves[:3])}… → intención = {intencion}", prioridad, cond, lambda h: fijar(h, intencion))

    por_palabras("R1", "saludo", 40)
    por_palabras("R2", "horario", 60)
    por_palabras("R3", "ubicacion", 60)
    por_palabras("R4", "precios", 70, extra=lambda h: not h.lineas)
    por_palabras("R5", "catalogo", 55)
    # "cuánto cuesta 20 básico" también es una cotización
    regla("R6", "Si contiene cotizar, presupuesto… → intención = cotizar", 90,
          lambda h: h.intencion is None and (contiene(h.norm, PALABRAS_CLAVE["cotizar"])
                                             or (contiene(h.norm, PALABRAS_CLAVE["precios"]) and bool(h.lineas))),
          lambda h: fijar(h, "cotizar"))
    por_palabras("R7", "pedido", 80)
    por_palabras("R8", "medios_pago", 65)
    por_palabras("R9", "entrega", 64, extra=lambda h: h.conv.estado == "idle")  # en plena cotización "envío" lo trata R20
    por_palabras("R10", "derivar", 95)
    por_palabras("R11", "cierre", 40)

    def cond_r12(h):
        en_flujo_con_datos = h.conv.estado != "idle" and (h.producto or h.cantidad is not None or h.lineas or h.entrega)
        return h.intencion is None and not en_flujo_con_datos

    def a_r12(h):
        h.intencion = FUERA_DE_DOMINIO
        h.conv.fuera_dominio_seguidas += 1
        h.partes.append(TXT_FUERA)

    regla("R12", "Si ninguna regla R1–R11 se cumple → intención = fuera_de_dominio", 5, cond_r12, a_r12)

    # ---------- R13 a R16: cotización guiada ----------
    def cond_r13(h):
        return (h.cotizando and not h.lineas and h.producto is None
                and (h.cantidad is None or ok(h.cantidad))
                and (h.intencion in INTENCIONES_COTIZACION or h.cantidad is not None))

    def a_r13(h):
        h.conv.estado = "esperando_producto"
        nota = ""
        if h.cantidad is not None:
            h.conv.cantidad_pendiente = h.cantidad
            nota = f"Anoté {h.cantidad} unidades. "
        h.partes.append(f"{nota}¿Qué producto deseas cotizar?\n" + lista_productos())

    regla("R13", "Si cotiza y no hay producto → preguntar qué producto desea", 70, cond_r13, a_r13)

    def a_r14(h):
        h.conv.estado = "esperando_cantidad"
        h.conv.producto_pendiente = h.producto
        h.partes.append(f"¿Cuántas unidades de **{h.producto.nombre}** necesitas?")

    regla("R14", "Si hay producto válido y no hay cantidad → preguntar la cantidad", 70,
          lambda h: h.cotizando and h.producto is not None and not h.lineas, a_r14)

    def a_r15(h):
        invalidas = [p for p, c in h.lineas if not ok(c)]
        h.conv.producto_pendiente = invalidas[0] if invalidas else h.producto
        h.conv.cantidad_pendiente = None
        h.conv.estado = "esperando_cantidad"
        h.partes.append(f"La cantidad debe ser un número entero entre 1 y {negocio.cantidad_maxima}. ¿Cuántas unidades necesitas?")

    regla("R15", "Si la cantidad no es un entero positivo (o supera el máximo) → pedir corrección", 70,
          lambda h: h.cotizando and (any(not ok(c) for _, c in h.lineas) or (h.cantidad is not None and not ok(h.cantidad))),
          a_r15)

    def a_r16(h):
        for prod, cant in h.lineas:
            previo = next((i for i in h.conv.items if i.producto.sku == prod.sku), None)
            if previo:  # mismo producto: se suma y se reevalúa el tramo de descuento
                previo.cantidad += cant
                previo.descuento_pct = None
            else:
                h.conv.items.append(Item(prod, cant))
        h.conv.producto_pendiente = h.conv.cantidad_pendiente = None
        h.conv.estado = "cotizado"
        h.recalcular = True

    regla("R16", "Si hay producto y cantidad válidos → agregar ítem a la cotización", 70,
          lambda h: h.cotizando and bool(h.lineas) and all(ok(c) for _, c in h.lineas), a_r16)

    # ---------- R17 a R19: descuento por tramo (se generan desde negocio.json) ----------
    tramos = negocio.descuentos
    for i, (desde, pct) in enumerate(tramos):
        hasta = tramos[i + 1][0] if i + 1 < len(tramos) else None

        def en_tramo(it, desde=desde, hasta=hasta):
            return it.descuento_pct is None and it.cantidad >= desde and (hasta is None or it.cantidad < hasta)

        def a_desc(h, en_tramo=en_tramo, pct=pct):
            for it in h.conv.items:
                if en_tramo(it):
                    it.descuento_pct = pct

        regla(f"R{17 + i}", f"Si cantidad ≥ {desde} → descuento {pct * 100:.0f} %", 50,
              lambda h, en_tramo=en_tramo: any(en_tramo(it) for it in h.conv.items), a_desc)

    # ---------- R20 a R23: envío, cálculo, presentación y derivación por monto ----------
    def cond_r20(h):
        return (h.entrega and not h.conv.entrega_solicitada and h.cotizando
                and (h.intencion in INTENCIONES_COTIZACION or bool(h.lineas) or contiene(h.norm, VERBOS_AGREGAR)))

    def a_r20(h):
        h.conv.entrega_solicitada = True
        if h.conv.items:
            h.recalcular = True
        else:
            h.partes.append("Anotado: tu pedido incluirá envío a domicilio.")

    regla("R20", "Si pide entrega → agregar costo de envío", 45, cond_r20, a_r20)

    regla("R21", "Si hay ítems → calcular subtotal, descuento, IGV y total", 30,
          lambda h: h.recalcular and bool(h.conv.items) and h.cotizacion is None,
          lambda h: setattr(h, "cotizacion", calcular(h.conv.items, negocio, h.conv.entrega_solicitada)))

    regla("R22", "Si hay presupuesto → mostrarlo con vigencia y aviso de monto estimado", 20,
          lambda h: h.cotizacion is not None,
          lambda h: h.partes.append(formatear_markdown(h.cotizacion, negocio, ofrecer_envio=not h.conv.entrega_solicitada)))

    def a_r23(h):
        h.derivar = True
        h.partes.append(f"⚠️ Como el monto supera {soles(negocio.umbral_derivacion)}, la dueña del negocio validará este presupuesto contigo. "
                        "Usa los botones de abajo para enviarle tu pedido.")

    regla("R23", "Si el total supera el umbral → derivar para validar el presupuesto", 10,
          lambda h: h.cotizacion is not None and h.cotizacion.total > negocio.umbral_derivacion, a_r23)

    # ---------- R24: derivación por desconcierto ----------
    def a_r24(h):
        h.derivar = True
        h.conv.fuera_dominio_seguidas = 0
        h.partes.append("Parece que no puedo resolver tu consulta. Te derivo con una persona: usa los botones de abajo.")

    regla("R24", "Si hay 2 consultas fuera de dominio seguidas → derivar a WhatsApp o correo", 4,
          lambda h: h.intencion == FUERA_DE_DOMINIO and h.conv.fuera_dominio_seguidas >= 2, a_r24)

    return reglas
