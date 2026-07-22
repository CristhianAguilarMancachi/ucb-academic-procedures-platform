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
) -> str:
    """
    Convierte la pregunta actual en una consulta autónoma.
    Si no hay historial, devuelve la pregunta tal como vino.
    Si hay historial, usa el LLM local para reinterpretar la pregunta actual
    considerando seguimiento conversacional, redacción pobre o ambigüedad moderada.
    """
    question = question.strip()

    if not conversation_history:
        return question

    history_text = build_history_text(conversation_history, max_turns=8)

    if not history_text:
        return question

    prompt = f"""
Tu tarea es convertir la última consulta del usuario en una pregunta autónoma y clara,
lista para buscar información en documentos institucionales.

Reglas:
- Mantén el idioma en español.
- Si la consulta ya es autosuficiente, devuélvela casi igual.
- Si depende del historial, intégralo y conviértela en una pregunta completa.
- Si la consulta tiene errores menores, redacción pobre o es ambigua pero recuperable, interprétala de la forma más probable usando el historial.
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