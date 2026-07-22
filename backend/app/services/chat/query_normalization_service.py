from __future__ import annotations

import re


def normalize_user_question(question: str) -> str:
    """
    Limpia la consulta del usuario sin cambiar su intención.
    No intenta corregir completamente ortografía ni rehacer la pregunta;
    solo la deja en una forma más estable para el LLM y el retrieval.
    """
    q = question.strip()

    # Normalizar espacios
    q = re.sub(r"\s+", " ", q)

    # Compactar signos repetidos
    q = re.sub(r"[?]{2,}", "?", q)
    q = re.sub(r"[!]{2,}", "!", q)
    q = re.sub(r"[.]{3,}", "...", q)

    # Limpiar espacios antes de signos
    q = re.sub(r"\s+([?,.!:;])", r"\1", q)

    # Si termina sin signo y parece pregunta, no forzar nada.
    return q