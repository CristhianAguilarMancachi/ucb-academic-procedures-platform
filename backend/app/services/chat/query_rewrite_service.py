from __future__ import annotations

import re

from app.services.rag.llm_client import (
    complete_text,
    LLMUnavailableError,
)
from app.services.rag.topic_router import detect_allowed_documents


def build_history_text(
    conversation_history: list[dict[str, str]],
    max_turns: int = 6,
) -> str:
    relevant = conversation_history[-max_turns:]

    lines: list[str] = []

    for msg in relevant:
        role = msg.get("role", "").strip().lower()
        content = msg.get("content", "").strip()

        if not content:
            continue

        if role == "user":
            lines.append(
                f"Usuario: {content}"
            )

        elif role == "assistant":
            lines.append(
                f"Asistente: {content}"
            )

    return "\n".join(lines)


def extract_rewritten_question(
    raw_text: str,
    fallback_question: str,
) -> str:
    text = raw_text.strip()

    if not text:
        return fallback_question.strip()

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

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
            candidate = (
                candidate[
                    len(prefix):
                ]
                .strip()
            )

            break

    return (
        candidate
        if candidate
        else fallback_question.strip()
    )


def contains_history_reference(
    question: str,
) -> bool:
    q = question.lower().strip()

    reference_patterns = [
        r"\besa prueba\b",
        r"\bese trámite\b",
        r"\bese tramite\b",
        r"\besa modalidad\b",
        r"\besa evaluación\b",
        r"\besa evaluacion\b",
        r"\bese proceso\b",
        r"\bese requisito\b",
        r"\besa nota\b",
        r"\bese documento\b",

        r"\besto\b",
        r"\beso\b",
        r"\baquello\b",

        r"\blo anterior\b",
        r"\bel anterior\b",
        r"\bla anterior\b",

        r"\bel mismo\b",
        r"\bla misma\b",
        r"\blos mismos\b",
        r"\blas mismas\b",
    ]

    for pattern in reference_patterns:
        if re.search(
            pattern,
            q,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def starts_like_follow_up(
    question: str,
) -> bool:
    q = (
        question.lower()
        .strip()
        .lstrip("¿¡")
        .strip()
    )

    follow_up_prefixes = [
        "y ",
        "pero ",
        "entonces ",
        "además ",
        "ademas ",
        "también ",
        "tambien ",
        "en ese caso",
        "y si ",
        "y qué ",
        "y que ",
        "y cómo ",
        "y como ",
        "y cuánto ",
        "y cuanto ",
        "y cuáles ",
        "y cuales ",
    ]

    return any(
        q.startswith(prefix)
        for prefix in follow_up_prefixes
    )


def contains_implicit_history_reference(
    question: str,
) -> bool:
    """
    Detecta consultas que dependen del turno anterior aunque
    no contengan pronombres explícitos como "eso" o "ese trámite".

    Se limita a construcciones lingüísticas típicamente elípticas
    para no convertir cualquier pregunta corta en un follow-up.
    """

    q = (
        question.lower()
        .strip()
        .lstrip("¿¡")
        .strip()
    )

    patterns = [
        # Referencias temporales a un plazo mencionado antes.
        r"\bya\s+(?:pasaron|transcurrieron|vencieron|expiraron)\b",
        r"\b(?:ese|el)\s+plazo\b",

        # Demostrativos cuyo referente normalmente está en el historial.
        r"\b(?:ese|esa|esos|esas|este|esta|estos|estas)\b",

        # Preguntas breves que omiten el objeto porque ya fue mencionado.
        r"^(?:y\s+)?(?:cuánto|cuanto)\s+(?:cuesta|tarda|demora)\b",
        r"^(?:y\s+)?(?:cuántos|cuantos|cuántas|cuantas)\s+"
        r"(?:necesito|son|debo)\b",
        r"^(?:y\s+)?(?:quién|quien|quiénes|quienes)\s+"
        r"(?:(?:lo|la|los|las|se)\s+)?",
        r"^(?:y\s+)?(?:dónde|donde|cuándo|cuando)\b",

        # Continuaciones procedimentales.
        r"^(?:y\s+)?(?:qué|que)\s+(?:debo|tengo)\s+que\s+hacer\s+"
        r"(?:ahora|después|despues|si\s+ya)\b",

        # Continuaciones sobre consecuencias.
        r"^(?:y\s+)?(?:qué|que)\s+"
        r"(?:pasa|ocurre|sucede)\s+"
        r"(?:ahora|después|despues|si)\b",
    ]

    return any(
        re.search(
            pattern,
            q,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


def should_rewrite_question(
    question: str,
    query_type: str,
) -> bool:
    q = question.strip()

    if not q:
        return False

    # Referencias explícitas al historial.
    if contains_history_reference(q):
        return True

    # Continuaciones como:
    # "¿Y qué pasa si la repruebo?"
    if starts_like_follow_up(q):
        return True

    # Referencias implícitas como:
    # "¿Cuánto cuesta?"
    # "¿Quién lo revisa?"
    # "¿Qué debo hacer si ya pasó el plazo?"
    if contains_implicit_history_reference(q):
        return True

    # Si la pregunta ya identifica claramente un tema
    # institucional, no hace falta reformularla.
    direct_documents = detect_allowed_documents(
        q
    )

    if direct_documents:
        return False

    # No asumimos que toda pregunta corta depende del historial.
    # Esto evita arrastrar el tema anterior hacia una consulta nueva
    # y no relacionada.
    return False


def rewrite_question_with_history(
    question: str,
    conversation_history: list[dict[str, str]] | None = None,
    query_type: str = "general",
) -> str:
    question = question.strip()

    if not question:
        return question

    if not conversation_history:
        return question

    # Si la pregunta ya es autosuficiente,
    # no llamamos a Groq.
    if not should_rewrite_question(
        question=question,
        query_type=query_type,
    ):
        return question

    history_text = build_history_text(
        conversation_history,
        max_turns=6,
    )

    if not history_text:
        return question

    prompt = f"""
Convierte únicamente la ÚLTIMA consulta del usuario en una pregunta
autónoma que pueda entenderse sin leer el historial.

TIPO DE CONSULTA:
{query_type}

UTILIZA EL HISTORIAL SOLO PARA RESOLVER REFERENCIAS NECESARIAS.

Ejemplo:

Historial:
Usuario: ¿Qué es la prueba de suficiencia?
Asistente: ...

Nueva consulta:
¿Y qué pasa si la repruebo?

Salida correcta:
¿Qué pasa si repruebo la prueba de suficiencia?

REGLAS:

- No respondas la pregunta.
- No expliques nada.
- Devuelve únicamente una pregunta.
- Mantén el idioma español.
- Conserva la intención exacta del usuario.
- No agregues información que el usuario no haya preguntado.
- No mezcles temas diferentes del historial.
- No arrastres automáticamente el tema de la consulta anterior.
- Usa el historial únicamente cuando sea necesario para sustituir
  referencias como:
  "eso",
  "esa prueba",
  "ese trámite",
  "esa modalidad",
  "la anterior",
  "lo anterior",
  "la misma".
- No agregues notas, plazos, porcentajes, condiciones,
  requisitos, artículos ni conceptos adicionales.
- Si existe más de un posible referente y no puedes identificar
  cuál corresponde con seguridad, conserva la consulta original.

HISTORIAL RECIENTE:
{history_text}

ÚLTIMA CONSULTA:
{question}

PREGUNTA AUTÓNOMA:
""".strip()

    try:
        rewritten = complete_text(
            prompt,
            temperature=0.0,
            max_completion_tokens=128,
            reasoning_effort="low",
            task="rewrite",
        )

    except LLMUnavailableError:
        # El rewrite es auxiliar.
        # Si falla Groq, conservamos la pregunta original.
        return question

    final_question = (
        extract_rewritten_question(
            raw_text=rewritten,
            fallback_question=question,
        )
    )

    # Evita reformulaciones exageradamente largas
    # que probablemente arrastraron demasiado historial.
    original_words = len(
        question.split()
    )

    rewritten_words = len(
        final_question.split()
    )

    if rewritten_words > max(
        original_words * 3,
        24,
    ):
        return question

    return final_question