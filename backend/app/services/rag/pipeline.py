from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.core.config import TOP_K
from app.services.chat.query_normalization_service import (
    normalize_user_question,
)
from app.services.chat.query_rewrite_service import (
    rewrite_question_with_history,
)
from app.services.rag.answer_router import (
    try_intent_based_answer,
)
from app.services.rag.generator import (
    generate_answer,
)
from app.services.rag.prompt_builder import (
    AMBIGUOUS_MESSAGE,
    NO_INFORMATION_MESSAGE,
)
from app.services.rag.query_classifier import (
    classify_query,
)
from app.services.rag.response_builder import (
    ANSWER_STATUS_ANSWERED,
    ANSWER_STATUS_PARTIAL,
    build_structured_response,
    render_response,
)
from app.services.rag.retrieval_hints import (
    get_retrieval_hints,
)
from app.services.rag.retriever import (
    retrieve_relevant_chunks,
)
from app.services.rag.source_ranker import (
    rank_sources_by_support,
)
from app.services.rag.topic_router import (
    detect_allowed_documents,
)


def try_exact_answer(
    question: str,
    documents: list[str],
) -> dict | None:
    q = question.lower().strip()

    combined = "\n".join(
        documents
    )

    # ---------------------------------------------------------
    # NOTA MÍNIMA
    # ---------------------------------------------------------

    if (
        "nota mínima" in q
        or "nota minima" in q
    ):
        match = re.search(
            (
                r"nota\s+m[ií]nima\s+"
                r"(?:de\s+)?aprobaci[oó]n"
                r".{0,80}?"
                r"(\d+)\s*(?:puntos)?"
                r"\s*(?:sobre|/)\s*100"
            ),
            combined,
            re.IGNORECASE
            | re.DOTALL,
        )

        if match:
            return build_structured_response(
                answer_type="quantity",
                answer_text=(
                    "La nota mínima de aprobación es de "
                    f"{match.group(1)} puntos sobre 100."
                ),
                grounded=True,
                status=ANSWER_STATUS_ANSWERED,
            )

    # ---------------------------------------------------------
    # HORAS DE FORMACIÓN INTEGRAL
    # ---------------------------------------------------------

    if (
        "cuántas horas" in q
        or "cuantas horas" in q
    ):
        match = re.search(
            (
                r"(?:cumplir|acreditar)"
                r".{0,60}?"
                r"(\d+)\s+horas"
                r".{0,60}?"
                r"formaci[oó]n\s+integral"
            ),
            combined,
            re.IGNORECASE
            | re.DOTALL,
        )

        if match:
            return build_structured_response(
                answer_type="quantity",
                answer_text=(
                    "Un estudiante debe cumplir "
                    f"{match.group(1)} horas académicas "
                    "de Formación Integral."
                ),
                grounded=True,
                status=ANSWER_STATUS_ANSWERED,
            )

    # ---------------------------------------------------------
    # CURSOS / TALLERES DE FORMACIÓN INTEGRAL
    # ---------------------------------------------------------

    if any(
        text in q
        for text in [
            "cuántos talleres",
            "cuantos talleres",
            "cuántos cursos",
            "cuantos cursos",
        ]
    ):
        match = re.search(
            (
                r"(?:acreditar|cumplir)"
                r".{0,60}?"
                r"(\d+)"
                r".{0,30}?"
                r"(?:talleres|cursos)"
            ),
            combined,
            re.IGNORECASE
            | re.DOTALL,
        )

        if match:
            return build_structured_response(
                answer_type="quantity",
                answer_text=(
                    "Los estudiantes deben acreditar "
                    f"{match.group(1)} cursos o talleres completos."
                ),
                grounded=True,
                status=ANSWER_STATUS_ANSWERED,
            )

    # ---------------------------------------------------------
    # CONTACTO
    # ---------------------------------------------------------

    if any(
        text in q
        for text in [
            "correo",
            "contacto",
            "beca",
            "posgrado",
            "exterior",
        ]
    ):
        email_match = re.search(
            (
                r"[A-Za-z0-9._%+-]+"
                r"@[A-Za-z0-9.-]+"
                r"\.[A-Za-z]{2,}"
            ),
            combined,
        )

        if email_match:
            return build_structured_response(
                answer_type="contact",
                answer_text=(
                    "El estudiante debe comunicarse con la "
                    "Analista Académica al correo "
                    f"{email_match.group(0)} y explicar qué "
                    "documentos le solicitaron exactamente."
                ),
                grounded=True,
                status=ANSWER_STATUS_ANSWERED,
            )

    return None


def clean_final_answer(
    answer: str,
) -> str:
    answer = answer.strip()

    answer = answer.replace(
        "**",
        "",
    )

    answer = answer.replace(
        "__",
        "",
    )

    answer = answer.replace(
        "Debera",
        "Deberá",
    )

    answer = answer.replace(
        "debera",
        "deberá",
    )

    return answer.strip()


def is_no_information_answer(
    answer: str,
) -> bool:
    normalized = (
        answer
        .lower()
        .strip()
    )

    return (
        NO_INFORMATION_MESSAGE.lower()
        in normalized
    )


def is_ambiguous_answer(
    answer: str,
) -> bool:
    normalized = (
        answer
        .lower()
        .strip()
    )

    return (
        AMBIGUOUS_MESSAGE.lower()
        in normalized
    )


def detect_answer_status(
    answer: str,
) -> str:
    normalized = (
        answer
        .lower()
        .strip()
    )

    partial_markers = [
        "no se encontró información suficiente para",
        "no se encontro informacion suficiente para",
        "no se dispone de información suficiente para",
        "no se dispone de informacion suficiente para",
        "la información disponible no permite",
        "la informacion disponible no permite",
        "no está especificado en los documentos",
        "no esta especificado en los documentos",
        "no aparece en los documentos disponibles",
        "no se encontró en los documentos",
        "no se encontro en los documentos",
        "no está indicado en los documentos",
        "no esta indicado en los documentos",
        "el contexto no especifica",
        "los documentos no especifican",
        "la información disponible no especifica",
        "la informacion disponible no especifica",
    ]

    if any(
        marker in normalized
        for marker in partial_markers
    ):
        return ANSWER_STATUS_PARTIAL

    return ANSWER_STATUS_ANSWERED


def build_pipeline_result(
    *,
    original_question: str,
    normalized_question: str,
    standalone_question: str,
    answer: str,
    sources: list[dict],
) -> dict:
    return {
        "question": original_question,
        "standalone_question": (
            standalone_question
            if standalone_question
            != normalized_question
            else None
        ),
        "answer": answer,
        "sources": sources,
    }


def run_rag_pipeline(
    db: Session,
    question: str,
    conversation_history: list[dict[str, str]] | None = None,
    top_k: int | None = None,
) -> dict:
    effective_top_k = (
        top_k
        or TOP_K
    )

    # ---------------------------------------------------------
    # 1. NORMALIZACIÓN
    # ---------------------------------------------------------

    normalized_question = (
        normalize_user_question(
            question
        )
    )

    # ---------------------------------------------------------
    # 2. CLASIFICACIÓN
    # ---------------------------------------------------------

    query_type = classify_query(
        normalized_question
    )

    # ---------------------------------------------------------
    # 3. REFORMULACIÓN CON HISTORIAL
    # ---------------------------------------------------------

    standalone_question = (
        rewrite_question_with_history(
            question=normalized_question,
            conversation_history=(
                conversation_history
                or []
            ),
            query_type=query_type,
        )
    )

    if (
        len(
            standalone_question.split()
        )
        > max(
            len(
                normalized_question.split()
            )
            * 3,
            24,
        )
    ):
        standalone_question = (
            normalized_question
        )

    # ---------------------------------------------------------
    # 4. ROUTING DE DOCUMENTOS
    # ---------------------------------------------------------

    allowed_documents = (
        detect_allowed_documents(
            standalone_question
        )
    )

    # ---------------------------------------------------------
    # 5. HINTS
    # ---------------------------------------------------------

    retrieval_hints = (
        get_retrieval_hints(
            query_type=query_type,
            question=standalone_question,
        )
    )

    # ---------------------------------------------------------
    # 6. RETRIEVAL
    # ---------------------------------------------------------

    documents, metadatas = (
        retrieve_relevant_chunks(
            db=db,
            query=standalone_question,
            top_k=effective_top_k,
            allowed_documents=allowed_documents,
            query_type=query_type,
            retrieval_hints=retrieval_hints,
        )
    )

    # ---------------------------------------------------------
    # 7. SIN EVIDENCIA
    # ---------------------------------------------------------

    if not documents:
        if query_type == "ambiguous":
            return build_pipeline_result(
                original_question=question,
                normalized_question=normalized_question,
                standalone_question=standalone_question,
                answer=AMBIGUOUS_MESSAGE,
                sources=[],
            )

        return build_pipeline_result(
            original_question=question,
            normalized_question=normalized_question,
            standalone_question=standalone_question,
            answer=NO_INFORMATION_MESSAGE,
            sources=[],
        )

    # ---------------------------------------------------------
    # 8. RESPUESTA DETERMINÍSTICA
    # ---------------------------------------------------------

    structured_response = None

    if query_type in {
        "factoid",
        "contact",
    }:
        structured_response = (
            try_exact_answer(
                standalone_question,
                documents,
            )
        )

    # ---------------------------------------------------------
    # 9. ROUTER ESPECIAL
    # ---------------------------------------------------------

    if not structured_response:
        structured_response = (
            try_intent_based_answer(
                standalone_question,
                documents,
            )
        )

    # ---------------------------------------------------------
    # 10. GENERACIÓN
    # ---------------------------------------------------------

    if not structured_response:
        llm_answer = generate_answer(
            question=standalone_question,
            documents=documents,
            metadatas=metadatas,
            query_type=query_type,
        )

        llm_answer = clean_final_answer(
            llm_answer
        )

        if is_no_information_answer(
            llm_answer
        ):
            return build_pipeline_result(
                original_question=question,
                normalized_question=normalized_question,
                standalone_question=standalone_question,
                answer=NO_INFORMATION_MESSAGE,
                sources=[],
            )

        if is_ambiguous_answer(
            llm_answer
        ):
            return build_pipeline_result(
                original_question=question,
                normalized_question=normalized_question,
                standalone_question=standalone_question,
                answer=AMBIGUOUS_MESSAGE,
                sources=[],
            )

        answer_status = (
            detect_answer_status(
                llm_answer
            )
        )

        structured_response = (
            build_structured_response(
                answer_type=query_type,
                answer_text=llm_answer,
                grounded=True,
                status=answer_status,
            )
        )

    # ---------------------------------------------------------
    # 11. RENDER
    # ---------------------------------------------------------

    answer = render_response(
        structured_response
    )

    answer = clean_final_answer(
        answer
    )

    # ---------------------------------------------------------
    # 12. SIN INFORMACIÓN / AMBIGÜEDAD
    # ---------------------------------------------------------

    if is_no_information_answer(
        answer
    ):
        return build_pipeline_result(
            original_question=question,
            normalized_question=normalized_question,
            standalone_question=standalone_question,
            answer=NO_INFORMATION_MESSAGE,
            sources=[],
        )

    if is_ambiguous_answer(
        answer
    ):
        return build_pipeline_result(
            original_question=question,
            normalized_question=normalized_question,
            standalone_question=standalone_question,
            answer=AMBIGUOUS_MESSAGE,
            sources=[],
        )

    # ---------------------------------------------------------
    # 13. REORDENAR FUENTES SEGÚN RESPALDO
    # ---------------------------------------------------------

    ranked_sources = (
        rank_sources_by_support(
            question=standalone_question,
            answer=answer,
            documents=documents,
            metadatas=metadatas,
        )
    )

    # ---------------------------------------------------------
    # 14. RESPUESTA FINAL
    # ---------------------------------------------------------

    return build_pipeline_result(
        original_question=question,
        normalized_question=normalized_question,
        standalone_question=standalone_question,
        answer=answer,
        sources=ranked_sources,
    )