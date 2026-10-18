from __future__ import annotations

import logging

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from app.core.dependencies import (
    obtener_usuario_actual,
    obtener_usuario_activo,
    UsuarioActivo,
)
from app.models.usuario import Usuario
from app.models.chat.chat_session import ChatSession
from app.models.chat.chat_message import ChatMessage
from app.models.chat.chat_message_feedback import ChatMessageFeedback

from app.db.session import get_db

from app.schemas.chat.chat import (
    RagChatQueryRequest,
    RagChatQueryResponse,
    RagCurrentChatResponse,
    RagClearChatResponse,
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
    get_chat_session,
    get_user_chat_session,
    get_or_create_user_chat_session,
    delete_user_chat,
    save_chat_message,
)

from app.services.rag.llm_client import (
    LLMUnavailableError,
    UNAVAILABLE_MESSAGE,
)

from app.services.chat.visitor_session import (
    read_visitor_id,
    set_visitor_cookie,
    delete_visitor_cookie,
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


optional_bearer = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    auto_error=False,
)


def obtener_usuario_rag_opcional(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Depends(optional_bearer),
) -> Usuario | None:
    # No aceptar como visitante una solicitud que presente
    # explícitamente credenciales inválidas.
    if token is None:
        if request.headers.get("Authorization"):
            raise HTTPException(
                status_code=401,
                detail="Credenciales no válidas.",
            )
        return None

    usuario = obtener_usuario_actual(db, token)
    return obtener_usuario_activo(usuario)


def validar_sesion_rag(
    db: Session,
    session_id: UUID,
    usuario: Usuario | None,
    request: Request,
) -> None:
    session = db.scalar(
        select(ChatSession).where(
            ChatSession.id_session == session_id
        )
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="La conversación no existe.",
        )

    if usuario is None:
        permitido = (
            session.id_usuario is None
            and read_visitor_id(request) == session_id
        )
    else:
        permitido = session.id_usuario == usuario.id_usuario

    if not permitido:
        raise HTTPException(
            status_code=404,
            detail="La conversación no existe.",
        )


@router.get(
    "/session",
    response_model=RagCurrentChatResponse,
)
def current_rag_session(
    usuario: UsuarioActivo,
    db: Session = Depends(get_db),
):
    session = get_user_chat_session(db, usuario.id_usuario)

    if session is None:
        return RagCurrentChatResponse()

    mensajes = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id_session)
        .order_by(ChatMessage.message_order.asc())
    ).all()

    valoraciones = {
        item.message_id: item.rating
        for item in db.scalars(
            select(ChatMessageFeedback)
            .join(
                ChatMessage,
                ChatMessage.id_message
                == ChatMessageFeedback.message_id,
            )
            .where(
                ChatMessage.session_id == session.id_session
            )
        ).all()
    }

    return RagCurrentChatResponse(
        session_id=session.id_session,
        messages=[
            {
                "id_message": m.id_message,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
                "sources_json": m.sources_json,
                "feedback_rating": valoraciones.get(m.id_message),
            }
            for m in mensajes
        ],
    )


@router.delete(
    "/session",
    response_model=RagClearChatResponse,
)
def clear_rag_session(
    request: Request,
    response: Response,
    usuario: Usuario | None = Depends(
        obtener_usuario_rag_opcional
    ),
    db: Session = Depends(get_db),
):
    if usuario is not None:
        eliminado = delete_user_chat(
            db=db,
            id_usuario=usuario.id_usuario,
        )
    else:
        session_id = read_visitor_id(request)
        session = (
            get_chat_session(db, session_id)
            if session_id is not None
            else None
        )

        eliminado = (
            session is not None
            and session.id_usuario is None
        )

        if eliminado:
            db.delete(session)
            db.commit()

        delete_visitor_cookie(response)

    return RagClearChatResponse(
        deleted=eliminado,
        message="Conversación limpiada correctamente.",
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
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obtener_usuario_rag_opcional),
):
    # --------------------------------------------------------
    # 1. Obtener o crear sesión de conversación
    # --------------------------------------------------------

    if usuario is not None:
        session = get_or_create_user_chat_session(
            db=db,
            id_usuario=usuario.id_usuario,
        )
    else:
        visitor_id = read_visitor_id(request)
        visitor_session = (
            get_chat_session(db, visitor_id)
            if visitor_id is not None
            else None
        )

        # Nunca confiar en un UUID suministrado por Angular.
        session = get_or_create_chat_session(
            db=db,
            session_id=(
                visitor_id
                if visitor_session is not None
                and visitor_session.id_usuario is None
                else None
            ),
        )
        set_visitor_cookie(response, session.id_session)


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
    request: Request,
    payload: RagMessageFeedbackRequest,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obtener_usuario_rag_opcional),
):
    validar_sesion_rag(
        db=db,
        session_id=payload.session_id,
        usuario=usuario,
        request=request,
    )

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
    request: Request,

    session_id: UUID = Query(
        ...,
        description=(
            "Sesión de conversación a la que "
            "pertenece el mensaje."
        ),
    ),

    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(obtener_usuario_rag_opcional),
):
    validar_sesion_rag(
        db=db,
        session_id=session_id,
        usuario=usuario,
        request=request,
    )

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