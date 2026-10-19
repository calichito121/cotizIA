"""Chat por consola para probar el motor sin Streamlit:  python consola.py"""
from servicio import crear_asistente

asistente = crear_asistente()
conv = asistente.nueva_conversacion()
print(asistente.bienvenida(conv))
while True:
    try:
        msg = input("\n> ")
    except (EOFError, KeyboardInterrupt):
        break
    r = asistente.atender(msg, conv)
    print("\n" + r.texto + f"\n[reglas: {' → '.join(r.traza)}]")
