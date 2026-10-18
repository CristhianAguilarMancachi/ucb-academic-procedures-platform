from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================
# FUENTES
# ============================================================

class ChatSourceSchema(BaseModel):
    document: str | None = None
    page: int | None = None
    article_number: str | None = None
    chunk_strategy: str | None = None
    section: str | None = None
    subsection: str | None = None


# ============================================================
# MENSAJES
# ============================================================

class ChatMessageSchema(BaseModel):
    id_message: UUID
    session_id: UUID
    role: str
    content: str
    message_order: int
    sources_json: list[dict[str, Any]] | None = None
    created_at: datetime


# ============================================================
# SESIONES
# ============================================================

class ChatSessionSchema(BaseModel):
    id_session: UUID
    title: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================
# CONSULTA RAG
# ============================================================

class RagChatQueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
    )
    session_id: UUID | None = None


class RagChatQueryResponse(BaseModel):
    session_id: UUID

    # Identificador persistente del mensaje del asistente.
    # El frontend lo utiliza para registrar like/dislike.
    message_id: UUID

    question: str
    standalone_question: str | None = None
    answer: str

    sources: list[ChatSourceSchema] = Field(
        default_factory=list,
    )


# ============================================================
# FEEDBACK
# ============================================================



class RagStoredMessage(BaseModel):
    id_message: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    sources_json: list[dict[str, Any]] | None = None
    feedback_rating: Literal[-1, 1] | None = None


class RagCurrentChatResponse(BaseModel):
    session_id: UUID | None = None
    messages: list[RagStoredMessage] = Field(
        default_factory=list
    )


class RagClearChatResponse(BaseModel):
    deleted: bool
    message: str


class RagMessageFeedbackRequest(BaseModel):
    # Sesión de conversación a la que pertenece
    # el mensaje valorado.
    session_id: UUID

    #  1 = útil
    # -1 = no útil
    rating: Literal[-1, 1]


class RagMessageFeedbackResponse(BaseModel):
    id_feedback: UUID
    message_id: UUID
    rating: Literal[-1, 1]
    created_at: datetime
    updated_at: datetime


class RagMessageFeedbackDeleteResponse(BaseModel):
    message_id: UUID
    deleted: bool
    message: str