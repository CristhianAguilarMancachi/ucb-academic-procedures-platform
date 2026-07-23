from __future__ import annotations

from typing import Any

import requests

from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL


VALID_QUERY_TYPES = {
    "factoid",
    "definition",
    "procedure",
    "consequence",
    "eligibility",
    "comparison",
    "contact",
    "ambiguous",
    "general",
}


def heuristic_query_type(question: str) -> str | None:
    q = question.lower().strip()

    if not q:
        return "ambiguous"

    if len(q.split()) <= 2:
        return "ambiguous"

    if any(token in q for token in ["correo", "mail", "email", "beca", "posgrado", "exterior"]):
        return "contact"

    if any(token in q for token in ["qué es", "que es", "en que consiste", "qué significa", "que significa"]):
        return "definition"

    if any(token in q for token in ["qué pasa si", "que pasa si", "qué ocurre si", "que ocurre si", "repruebo", "reprueba", "reprobé", "reprobe"]):
        return "consequence"

    if any(token in q for token in ["puedo", "puede", "es posible", "se puede", "podria", "podría", "llego con", "alcanzar", "aprobar con"]):
        return "eligibility"

    if any(token in q for token in ["cómo", "como", "qué debo hacer", "que debo hacer", "qué tengo que hacer", "que tengo que hacer", "requisitos", "solicitar", "tramitar"]):
        return "procedure"

    if any(token in q for token in ["cuánto", "cuanto", "cuántas", "cuantas", "cuántos", "cuantos", "qué nota", "que nota", "qué plazo", "que plazo"]):
        return "factoid"

    if any(token in q for token in ["diferencia", "comparar", "comparación", "comparacion", "mejor que", "igual que"]):
        return "comparison"

    return None


def extract_label(raw_text: str) -> str:
    text = raw_text.strip().lower()

    for label in VALID_QUERY_TYPES:
        if text == label:
            return label

    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    for line in lines:
        if line in VALID_QUERY_TYPES:
            return line

    return "general"


def classify_query(question: str) -> str:
    heuristic = heuristic_query_type(question)
    if heuristic is not None:
        return heuristic

    prompt = f"""
Clasifica la siguiente consulta del usuario en una sola categoría.

Categorías permitidas:
- factoid
- definition
- procedure
- consequence
- eligibility
- comparison
- contact
- ambiguous
- general

Criterios:
- factoid: pide un dato puntual como nota, cantidad, plazo, número, requisito exacto.
- definition: pide definición o significado.
- procedure: pregunta qué hacer, cómo tramitar, pasos, requisitos o proceso.
- consequence: pregunta qué pasa si ocurre algo.
- eligibility: pregunta si puede o no puede hacer algo, o si cumple condición.
- comparison: compara dos opciones o situaciones.
- contact: pide correo o contacto.
- ambiguous: demasiado vaga, insuficiente o poco interpretable.
- general: consulta general que no encaja claramente en otra categoría.

Devuelve solo una palabra de la lista.

Consulta:
{question}
""".strip()

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0
                }
            },
            timeout=45,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return extract_label(data.get("response", "general"))
    except Exception:
        return "general"