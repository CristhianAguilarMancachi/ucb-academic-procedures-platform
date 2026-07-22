from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatSourceSchema(BaseModel):
    document: str | None = None
    page: int | None = None
    article_number: str | None = None
    chunk_strategy: str | None = None
    section: str | None = None
    subsection: str | None = None


class ChatMessageSchema(BaseModel):
    id_message: UUID
    session_id: UUID
    role: str
    content: str
    message_order: int
    sources_json: list[dict[str, Any]] | None = None
    created_at: datetime


class ChatSessionSchema(BaseModel):
    id_session: UUID
    title: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RagChatQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: UUID | None = None


class RagChatQueryResponse(BaseModel):
    session_id: UUID
    question: str
    standalone_question: str | None = None
    answer: str
    sources: list[ChatSourceSchema] = Field(default_factory=list)