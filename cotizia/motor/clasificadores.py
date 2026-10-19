"""Clasificadores de intención intercambiables.

- LineaBasePalabrasClave: alternativa A (semana 8). Se usa SOLO para comparar contra el sistema experto.
- ClasificadorML: semana 16. Envuelve un Pipeline de scikit-learn guardado con joblib.
"""
from __future__ import annotations

from typing import Protocol

from .utilidades import contiene, normalizar
from .vocabulario import FUERA_DE_DOMINIO, PALABRAS_CLAVE


class Clasificador(Protocol):
    def predecir(self, texto_norm: str) -> tuple[str | None, float]: ...


class LineaBasePalabrasClave:
    """Primera intención cuyo vocabulario aparece. Sin estado, sin prioridades, sin cálculo de montos."""

    def predecir(self, texto: str) -> str:
        norm = normalizar(texto)
        for intencion, claves in PALABRAS_CLAVE.items():
            if contiene(norm, claves):
                return intencion
        return FUERA_DE_DOMINIO


class ClasificadorML:
    """Semana 16: Pipeline(TfidfVectorizer, MultinomialNB o SVC(probability=True)) entrenado con las
    consultas etiquetadas del registro. Si la probabilidad no llega al umbral devuelve None y el
    motor cae a las reglas R1–R12 (modo híbrido)."""

    def __init__(self, ruta_modelo: str, umbral: float = 0.6):
        import joblib  # import perezoso: no hace falta en la semana 8

        self.pipeline = joblib.load(ruta_modelo)
        self.umbral = umbral

    def predecir(self, texto_norm: str) -> tuple[str | None, float]:
        probs = self.pipeline.predict_proba([texto_norm])[0]
        i = int(probs.argmax())
        etiqueta = str(self.pipeline.classes_[i])
        return (etiqueta, float(probs[i])) if probs[i] >= self.umbral else (None, float(probs[i]))
