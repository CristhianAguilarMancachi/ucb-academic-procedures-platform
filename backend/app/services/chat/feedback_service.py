from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from uuid import UUID

from sqlalchemy import select

from sqlalchemy.orm import Session

from app.models.chat.chat_message import (
    ChatMessage,
)

from app.models.chat.chat_message_feedback import (
    ChatMessageFeedback,
)


# ============================================================
# ERRORES DE DOMINIO
# ============================================================

class ChatFeedbackError(
    Exception,
):

    pass


class ChatMessageNotFoundError(
    ChatFeedbackError,
):

    pass


class ChatMessageNotRateableError(
    ChatFeedbackError,
):

    pass


class ChatFeedbackNotFoundError(
    ChatFeedbackError,
):

    pass


# ============================================================
# MENSAJE RATEABLE
# ============================================================

def get_rateable_message(
    db:
        Session,

    message_id:
        UUID,

    session_id:
        UUID,
) -> ChatMessage:

    stmt = (
        select(
            ChatMessage,
        )
        .where(
            ChatMessage.id_message
            ==
            message_id,
        )
        .where(
            ChatMessage.session_id
            ==
            session_id,
        )
    )


    message = db.scalar(
        stmt,
    )


    if message is None:

        raise (
            ChatMessageNotFoundError(
                "No se encontró la respuesta indicada."
            )
        )


    if (
        message.role
        !=
        "assistant"
    ):

        raise (
            ChatMessageNotRateableError(
                "Solo pueden valorarse respuestas "
                "del asistente."
            )
        )


    return message


# ============================================================
# OBTENER FEEDBACK
# ============================================================

def get_message_feedback(
    db:
        Session,

    message_id:
        UUID,
) -> ChatMessageFeedback | None:

    stmt = (
        select(
            ChatMessageFeedback,
        )
        .where(
            ChatMessageFeedback
            .message_id
            ==
            message_id,
        )
    )


    return db.scalar(
        stmt,
    )


# ============================================================
# CREAR / ACTUALIZAR FEEDBACK
# ============================================================

def set_message_feedback(
    db:
        Session,

    message_id:
        UUID,

    session_id:
        UUID,

    rating:
        int,
) -> ChatMessageFeedback:

    if (
        rating
        not in
        (
            -1,
            1,
        )
    ):

        raise ValueError(
            "La valoración debe ser 1 o -1."
        )


    get_rateable_message(
        db=db,
        message_id=message_id,
        session_id=session_id,
    )


    feedback = (
        get_message_feedback(
            db=db,
            message_id=message_id,
        )
    )


    if (
        feedback
        is None
    ):

        feedback = (
            ChatMessageFeedback(
                message_id=message_id,
                rating=rating,
            )
        )

        db.add(
            feedback,
        )

    else:

        feedback.rating = (
            rating
        )

        feedback.updated_at = (
            datetime.now(
                timezone.utc,
            )
        )


    db.commit()

    db.refresh(
        feedback,
    )


    return feedback


# ============================================================
# ELIMINAR FEEDBACK
# ============================================================

def delete_message_feedback(
    db:
        Session,

    message_id:
        UUID,

    session_id:
        UUID,
) -> None:

    get_rateable_message(
        db=db,
        message_id=message_id,
        session_id=session_id,
    )


    feedback = (
        get_message_feedback(
            db=db,
            message_id=message_id,
        )
    )


    if (
        feedback
        is None
    ):

        raise (
            ChatFeedbackNotFoundError(
                "La respuesta todavía no tiene "
                "una valoración."
            )
        )


    db.delete(
        feedback,
    )

    db.commit()