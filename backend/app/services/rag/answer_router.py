from __future__ import annotations

import re
import unicodedata

from app.services.rag.response_builder import (
    ANSWER_STATUS_ANSWERED,
    build_structured_response,
)


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize_text(
    text: str,
) -> str:
    normalized = (
        text
        .lower()
        .strip()
    )

    normalized = unicodedata.normalize(
        "NFD",
        normalized,
    )

    normalized = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized


# ============================================================
# ELEGIBILIDAD:
# EXCELENCIA + INHABILITACIONES
# ============================================================

def try_excellence_eligibility_answer(
    question: str,
    documents: list[str],
) -> dict | None:
    q = normalize_text(
        question,
    )

    if "excelencia" not in q:
        return None

    has_inhabilitation_term = any(
        term in q
        for term in [
            "inhabilitacion",
            "inhabilitaciones",
            "inhabilitado",
            "inhabilitada",
            "inhabilitados",
            "inhabilitadas",
        ]
    )

    if not has_inhabilitation_term:
        return None

    combined = normalize_text(
        "\n".join(
            documents,
        )
    )

    has_negative_evidence = any(
        evidence in combined
        for evidence in [
            "la respuesta es negativa",
            "no pueden postular",
            "no puede postular",
        ]
    )

    has_failure_equivalence = (
        "inhabilitaciones cuentan como reprobaciones"
        in combined
        or (
            "inhabilitaciones" in combined
            and "reprobaciones" in combined
        )
    )

    if not (
        has_negative_evidence
        and has_failure_equivalence
    ):
        return None

    return build_structured_response(
        answer_type="eligibility",
        answer_text=(
            "No. Un estudiante con inhabilitaciones "
            "no puede postular a la modalidad de "
            "Graduación por Excelencia, ya que las "
            "inhabilitaciones cuentan como reprobaciones."
        ),
        grounded=True,
        status=ANSWER_STATUS_ANSWERED,
    )


# ============================================================
# MODALIDADES DE GRADUACIÓN
# ============================================================

def try_graduation_modalities_answer(
    question: str,
    documents: list[str],
) -> dict | None:
    q = normalize_text(
        question,
    )

    asks_modalities = (
        "modalidades de graduacion" in q
        or (
            "modalidades" in q
            and "graduacion" in q
        )
    )

    if not asks_modalities:
        return None

    combined = normalize_text(
        "\n".join(
            documents,
        )
    )

    modality_patterns: list[
        tuple[str, str]
    ] = [
        (
            "Graduación Directa",
            r"\bgraduacion directa\b",
        ),
        (
            "Monografía",
            r"\bmonografia\b",
        ),
        (
            "Proyecto de Grado Técnico",
            r"\bproyecto de grado tecnico\b",
        ),
        (
            "Pasantía",
            r"\bpasantia\b",
        ),
        (
            "Tesis de Grado",
            r"\btesis de grado\b",
        ),
        (
            "Proyecto de Grado",
            r"\bproyecto de grado\b(?!\s+tecnico)",
        ),
        (
            "Trabajo Dirigido",
            r"\btrabajo dirigido\b",
        ),
        (
            "Examen de Grado",
            r"\bexamen de grado\b",
        ),
        (
            "Graduación por Excelencia",
            r"\bgraduacion por excelencia\b",
        ),
        (
            "Graduación Vía Diplomado",
            r"\bgraduacion via diplomado\b",
        ),
        (
            "Internado Rotatorio",
            r"\binternado rotatorio\b",
        ),
    ]

    modalities: list[str] = []

    for (
        label,
        pattern,
    ) in modality_patterns:
        if re.search(
            pattern,
            combined,
            re.IGNORECASE,
        ):
            modalities.append(
                label,
            )

    if not modalities:
        return None

    lines = [
        (
            "Las modalidades de graduación "
            "identificadas en el reglamento son:"
        ),
        "",
    ]

    lines.extend(
        f"{index}. {modality}"
        for (
            index,
            modality,
        )
        in enumerate(
            modalities,
            start=1,
        )
    )

    return build_structured_response(
        answer_type="list_modalities",
        answer_text="\n".join(
            lines,
        ),
        grounded=True,
        status=ANSWER_STATUS_ANSWERED,
    )


# ============================================================
# ROUTER DE RESPUESTAS DETERMINÍSTICAS
# ============================================================

def try_intent_based_answer(
    question: str,
    documents: list[str],
) -> dict | None:
    """
    Construye una respuesta determinística únicamente cuando
    la evidencia necesaria está explícitamente contenida en
    los documentos recuperados.

    Si ninguna regla segura aplica, devuelve None y el pipeline
    continúa normalmente hacia el generador RAG.
    """

    excellence_answer = (
        try_excellence_eligibility_answer(
            question=question,
            documents=documents,
        )
    )

    if excellence_answer:
        return excellence_answer

    modalities_answer = (
        try_graduation_modalities_answer(
            question=question,
            documents=documents,
        )
    )

    if modalities_answer:
        return modalities_answer

    return None