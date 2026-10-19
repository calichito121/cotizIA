"""Interfaz web de CotizIA (Streamlit). Toda la lógica vive en motor/ y servicio.py."""
from __future__ import annotations

import streamlit as st

from servicio import crear_asistente

st.set_page_config(page_title="CotizIA", page_icon="💬", layout="centered")


@st.cache_resource(show_spinner=False)
def obtener_asistente():
    return crear_asistente()  # el motor no guarda estado: se comparte entre sesiones


asistente = obtener_asistente()


def reiniciar() -> None:
    conv = asistente.nueva_conversacion()
    st.session_state.conv = conv
    st.session_state.mensajes = [{"rol": "assistant", "texto": asistente.bienvenida(conv)}]


if "conv" not in st.session_state:
    reiniciar()

with st.sidebar:
    st.header(asistente.negocio.nombre)
    modo_demo = st.toggle("Modo demo: mostrar reglas disparadas", value=False)
    st.button("🔄 Nueva conversación", on_click=reiniciar)
    st.caption("Prototipo del curso de IA y ML (UAP). No guardamos nombres ni teléfonos.")

st.title("💬 CotizIA")
st.caption("Consultas y presupuestos 24/7")

ACCESOS = {
    "🧾 Cotizar": "Quiero cotizar",
    "💲 Precios": "¿Cuáles son los precios?",
    "🕒 Horario": "¿A qué hora atienden?",
    "🧑 Asesor": "Quiero hablar con un asesor",
}
entrada = None
for col, (etiqueta, texto) in zip(st.columns(len(ACCESOS)), ACCESOS.items()):
    if col.button(etiqueta, use_container_width=True):
        entrada = texto


def pintar(m: dict) -> None:
    with st.chat_message(m["rol"]):
        st.markdown(m["texto"])
        if m.get("whatsapp"):
            st.markdown(f"[📲 Enviar por WhatsApp]({m['whatsapp']})  ·  [✉️ Enviar por correo]({m['mailto']})")
        if modo_demo and m.get("traza"):
            st.caption("Reglas disparadas: " + " → ".join(m["traza"]) + f"  ·  {m['ms']:.1f} ms")


for m in st.session_state.mensajes:
    pintar(m)

entrada = st.chat_input("Escribe tu consulta…") or entrada
if entrada:
    usuario = {"rol": "user", "texto": entrada}
    st.session_state.mensajes.append(usuario)
    pintar(usuario)
    resp = asistente.atender(entrada, st.session_state.conv)
    bot = {
        "rol": "assistant", "texto": resp.texto, "traza": list(resp.traza), "ms": resp.ms,
        "whatsapp": resp.whatsapp_url, "mailto": resp.mailto_url,
    }
    st.session_state.mensajes.append(bot)
    pintar(bot)
