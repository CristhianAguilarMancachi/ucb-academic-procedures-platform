from __future__ import annotations

import logging

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.schemas.chat.chat import (
    RagChatQueryRequest,
    RagChatQueryResponse,
    RagMessageFeedbackDeleteResponse,
    RagMessageFeedbackRequest,
    RagMessageFeedbackResponse,
)

from app.services.chat.feedback_service import (
    ChatFeedbackNotFoundError,
    ChatMessageNotFoundError,
    ChatMessageNotRateableError,
    delete_message_feedback,
    set_message_feedback,
)

from app.services.chat.history_service import (
    build_conversation_history,
    get_or_create_chat_session,
    save_chat_message,
)

from app.services.rag.llm_client import (
    LLMUnavailableError,
    UNAVAILABLE_MESSAGE,
)

from app.services.rag.pipeline import (
    run_rag_pipeline,
)


logger = logging.getLogger(
    __name__,
)


router = APIRouter(
    tags=[
        "RAG",
    ],
)


# ============================================================
# CONSULTA RAG
# ============================================================

@router.post(
    "/query",
    response_model=RagChatQueryResponse,
)
def query_rag(
    payload: RagChatQueryRequest,
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # 1. Obtener o crear sesión de conversación
    # --------------------------------------------------------

    session = get_or_create_chat_session(
        db=db,
        session_id=payload.session_id,
    )


    # --------------------------------------------------------
    # 2. Construir historial reciente
    # --------------------------------------------------------

    conversation_history = (
        build_conversation_history(
            db=db,
            session_id=session.id_session,
            limit=8,
        )
    )


    # --------------------------------------------------------
    # 3. Ejecutar RAG
    # --------------------------------------------------------

    try:
        result = run_rag_pipeline(
            db=db,
            question=payload.question,
            conversation_history=conversation_history,
        )

        answer = result.get(
            "answer",
        )

        if (
            not isinstance(
                answer,
                str,
            )
            or
            not answer.strip()
        ):
            raise LLMUnavailableError(
                reason="empty_pipeline_answer",
            )

    except LLMUnavailableError as exc:
        logger.warning(
            "[RAG][API] Consulta no completada "
            "por indisponibilidad del LLM. "
            "reason=%s",
            exc.reason,
        )

        result = {
            "question":
                payload.question,

            "standalone_question":
                None,

            "answer":
                UNAVAILABLE_MESSAGE,

            "sources":
                [],
        }


    # --------------------------------------------------------
    # 4. Guardar mensaje del usuario
    # --------------------------------------------------------

    save_chat_message(
        db=db,
        session_id=session.id_session,
        role="user",
        content=payload.question,
    )


    # --------------------------------------------------------
    # 5. Guardar respuesta del asistente
    #
    # IMPORTANTE:
    # guardamos el objeto retornado para poder recuperar
    # id_message y enviarlo al frontend.
    # --------------------------------------------------------

    assistant_message = save_chat_message(
        db=db,
        session_id=session.id_session,
        role="assistant",
        content=result["answer"],
        sources_json=result["sources"],
    )


    # --------------------------------------------------------
    # 6. Respuesta HTTP
    # --------------------------------------------------------

    return RagChatQueryResponse(
        session_id=
            session.id_session,

        message_id=
            assistant_message.id_message,

        question=
            result["question"],

        standalone_question=
            result.get(
                "standalone_question",
            ),

        answer=
            result["answer"],

        sources=
            result["sources"],
    )


# ============================================================
# CREAR / ACTUALIZAR VALORACIÓN
# ============================================================

@router.put(
    "/messages/{message_id}/feedback",
    response_model=RagMessageFeedbackResponse,
)
def put_message_feedback(
    message_id: UUID,
    payload: RagMessageFeedbackRequest,
    db: Session = Depends(get_db),
):
    try:
        feedback = set_message_feedback(
            db=db,
            message_id=message_id,
            session_id=payload.session_id,
            rating=payload.rating,
        )

    except ChatMessageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ChatMessageNotRateableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


    return RagMessageFeedbackResponse(
        id_feedback=
            feedback.id_feedback,

        message_id=
            feedback.message_id,

        rating=
            feedback.rating,

        created_at=
            feedback.created_at,

        updated_at=
            feedback.updated_at,
    )


# ============================================================
# ELIMINAR VALORACIÓN
# ============================================================

@router.delete(
    "/messages/{message_id}/feedback",
    response_model=RagMessageFeedbackDeleteResponse,
)
def remove_message_feedback(
    message_id: UUID,

    session_id: UUID = Query(
        ...,
        description=(
            "Sesión de conversación a la que "
            "pertenece el mensaje."
        ),
    ),

    db: Session = Depends(get_db),
):
    try:
        delete_message_feedback(
            db=db,
            message_id=message_id,
            session_id=session_id,
        )

    except ChatMessageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ChatMessageNotRateableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except ChatFeedbackNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


    return RagMessageFeedbackDeleteResponse(
        message_id=
            message_id,

        deleted=
            True,

        message=(
            "Valoración eliminada correctamente."
        ),
    )