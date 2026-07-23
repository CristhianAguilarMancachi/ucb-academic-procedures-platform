from __future__ import annotations

from typing import Any

import requests

from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL


def build_history_text(conversation_history: list[dict[str, str]], max_turns: int = 8) -> str:
    relevant = conversation_history[-max_turns:]

    lines: list[str] = []
    for msg in relevant:
        role = msg.get("role", "").strip().lower()
        content = msg.get("content", "").strip()

        if not content:
            continue

        if role == "user":
            lines.append(f"Usuario: {content}")
        elif role == "assistant":
            lines.append(f"Asistente: {content}")

    return "\n".join(lines)


def extract_rewritten_question(raw_text: str, fallback_question: str) -> str:
    text = raw_text.strip()

    if not text:
        return fallback_question.strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return fallback_question.strip()

    candidate = lines[0]

    prefixes = [
        "pregunta autónoma:",
        "pregunta autonoma:",
        "pregunta final:",
        "consulta reformulada:",
        "reformulación:",
        "reformulacion:",
        "standalone question:",
    ]

    lower_candidate = candidate.lower()
    for prefix in prefixes:
        if lower_candidate.startswith(prefix):
            candidate = candidate[len(prefix):].strip()
            break

    return candidate if candidate else fallback_question.strip()


def rewrite_question_with_history(
    question: str,
    conversation_history: list[dict[str, str]] | None = None,
    query_type: str = "general",
) -> str:
    question = question.strip()

    if not conversation_history:
        return question

    history_text = build_history_text(conversation_history, max_turns=8)
    if not history_text:
        return question

    prompt = f"""
Tu tarea es convertir la última consulta del usuario en una pregunta autónoma y clara,
lista para buscar información en documentos institucionales.

Tipo de consulta detectado:
{query_type}

Reglas:
- Mantén el idioma en español.
- Si la consulta ya es autosuficiente, devuélvela casi igual.
- Si depende del historial, úsalo solo para resolver referencias como "esa prueba", "eso", "ese trámite", "esa modalidad", "lo anterior".
- Si la nueva consulta introduce una intención nueva clara, NO arrastres detalles específicos de preguntas anteriores que no se mencionen en la consulta actual.
- Ejemplos de detalles que NO debes arrastrar salvo que la nueva consulta los mencione: notas específicas como 59, reprobación, inhabilitación, porcentajes, plazos, números concretos o condiciones particulares.
- Si la consulta está en primera persona, conviértela a una forma objetiva e institucional.
- Si parece una opinión ("piensas que...", "crees que..."), conviértela en una consulta normativa o académica objetiva.
- Si la consulta tiene errores menores, redacción pobre o ambigüedad moderada, interprétala de la forma más probable usando el historial.
- No respondas la pregunta.
- No expliques nada.
- No agregues artículos, páginas o referencias normativas.
- No inventes trámites, requisitos o conceptos que no aparezcan implícitamente en el historial.
- Devuelve solo una pregunta final, en una sola línea.

Historial reciente:
{history_text}

Última consulta del usuario:
{question}

Devuelve solo la pregunta autónoma final:
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
            timeout=60,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        rewritten = data.get("response", "")
        return extract_rewritten_question(rewritten, question)
    except Exception:
        return question