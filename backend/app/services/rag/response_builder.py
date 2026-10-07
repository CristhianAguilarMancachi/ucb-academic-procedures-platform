from __future__ import annotations

from typing import Any


ANSWER_STATUS_ANSWERED = "answered"
ANSWER_STATUS_PARTIAL = "partial"
ANSWER_STATUS_NO_INFORMATION = "no_information"
ANSWER_STATUS_AMBIGUOUS = "ambiguous"


def build_structured_response(
    answer_type: str,
    answer_text: str,
    grounded: bool = True,
    status: str = ANSWER_STATUS_ANSWERED,
) -> dict[str, Any]:
    return {
        "answer_type": answer_type,
        "answer_text": answer_text.strip(),
        "grounded": grounded,
        "status": status,
    }


def render_response(
    structured_response: dict[str, Any],
) -> str:
    answer_text = (
        structured_response
        .get(
            "answer_text",
            "",
        )
        .strip()
    )

    grounded = structured_response.get(
        "grounded",
        True,
    )

    status = structured_response.get(
        "status",
        ANSWER_STATUS_ANSWERED,
    )

    if not answer_text:
        return (
            "No se encontró información suficiente en los documentos "
            "cargados para responder con seguridad a esa consulta."
        )

    if status == ANSWER_STATUS_NO_INFORMATION:
        return (
            "No se encontró información suficiente en los documentos "
            "cargados para responder con seguridad a esa consulta."
        )

    if status == ANSWER_STATUS_AMBIGUOUS:
        return (
            "No se pudo identificar con claridad a qué trámite o "
            "situación te refieres. Intenta mencionar el trámite, "
            "modalidad o tema."
        )

    if not grounded:
        return (
            "No se encontró información suficiente en los documentos "
            "cargados para responder con seguridad a esa consulta."
        )

    return answer_text