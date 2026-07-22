import re
from sqlalchemy.orm import Session

from app.core.config import TOP_K
from app.services.chat.query_normalization_service import normalize_user_question
from app.services.chat.query_rewrite_service import rewrite_question_with_history
from app.services.rag.retriever import retrieve_relevant_chunks
from app.services.rag.generator import generate_answer
from app.services.rag.topic_router import detect_allowed_documents
from app.services.rag.answer_router import try_intent_based_answer
from app.services.rag.response_builder import build_structured_response, render_response


def try_exact_answer(question: str, documents: list[str]) -> dict | None:
    q = question.lower()
    combined = "\n".join(documents)

    if "nota mínima" in q or "nota minima" in q:
        match = re.search(
            r"nota minima de aprobaci[oó]n\s+ser[aá]\s+de\s+(\d+)\s+puntos\s+sobre\s+100",
            combined,
            re.IGNORECASE
        )
        if match:
            return build_structured_response(
                answer_type="quantity",
                answer_text=f"La nota mínima de aprobación es de {match.group(1)} puntos sobre 100.",
                grounded=True
            )

    if "cuántas oportunidades" in q or "cuantas oportunidades" in q:
        match = re.search(
            r"tendr[aá]n?\s+(\w+)\s+oportunidades\s+para\s+aprobar\s+la\s+evaluaci[oó]n\s+final",
            combined,
            re.IGNORECASE
        )
        if match:
            value = match.group(1).strip().lower()
            if value == "dos":
                answer = "Los estudiantes habilitados tienen dos oportunidades para aprobar la evaluación final."
            else:
                answer = f"Los estudiantes habilitados tienen {value} oportunidades para aprobar la evaluación final."

            return build_structured_response(
                answer_type="quantity",
                answer_text=answer,
                grounded=True
            )

    if "cuántas horas" in q or "cuantas horas" in q:
        match = re.search(
            r"deben\s+cumplir\s+(\d+)\s+horas\s+acad[eé]micas\s+de\s+formaci[oó]n\s+integral",
            combined,
            re.IGNORECASE
        )
        if match:
            return build_structured_response(
                answer_type="quantity",
                answer_text=f"Un estudiante debe cumplir {match.group(1)} horas académicas de formación integral.",
                grounded=True
            )

    if "cuántos talleres" in q or "cuantos talleres" in q or "cuántos cursos" in q or "cuantos cursos" in q:
        match = re.search(
            r"deben\s+acreditar\s+(\d+)\s+talleres\s+o\s+cursos\s+completos",
            combined,
            re.IGNORECASE
        )
        if match:
            return build_structured_response(
                answer_type="quantity",
                answer_text=f"Los estudiantes deben acreditar {match.group(1)} talleres o cursos completos.",
                grounded=True
            )

    if "correo" in q or "beca" in q or "posgrado" in q or "exterior" in q:
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", combined)
        if email_match and ("beca" in q or "posgrado" in q or "exterior" in q):
            return build_structured_response(
                answer_type="contact",
                answer_text=(
                    f"El estudiante debe comunicarse con la Analista Académica al correo "
                    f"{email_match.group(0)} y explicar qué documentos le pidieron exactamente."
                ),
                grounded=True
            )

    return None


def clean_final_answer(answer: str) -> str:
    answer = re.sub(r"[ \t]+", " ", answer).strip()
    answer = re.sub(r" *\n *", "\n", answer)
    answer = answer.replace("Debera", "Deberá")
    answer = answer.replace("debera", "deberá")
    answer = answer.replace("por la que", "por la cual")
    return answer


def run_rag_pipeline(
    db: Session,
    question: str,
    conversation_history: list[dict[str, str]] | None = None,
    top_k: int | None = None
) -> dict:
    effective_top_k = top_k or TOP_K

    normalized_question = normalize_user_question(question)

    standalone_question = rewrite_question_with_history(
        question=normalized_question,
        conversation_history=conversation_history or []
    )

    allowed_documents = detect_allowed_documents(standalone_question)

    documents, metadatas = retrieve_relevant_chunks(
        db=db,
        query=standalone_question,
        top_k=effective_top_k,
        allowed_documents=allowed_documents
    )

    if not documents:
        return {
            "question": question,
            "standalone_question": standalone_question if standalone_question != normalized_question else None,
            "answer": "No se encontró información suficiente en los documentos cargados.",
            "sources": []
        }

    structured_response = try_exact_answer(standalone_question, documents)

    if not structured_response:
        structured_response = try_intent_based_answer(standalone_question, documents)

    if not structured_response:
        llm_answer = generate_answer(question=standalone_question, context_chunks=documents)
        structured_response = build_structured_response(
            answer_type="general",
            answer_text=llm_answer,
            grounded=True
        )

    answer = render_response(structured_response)
    answer = clean_final_answer(answer)

    return {
        "question": question,
        "standalone_question": standalone_question if standalone_question != normalized_question else None,
        "answer": answer,
        "sources": metadatas
    }