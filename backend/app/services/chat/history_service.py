from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chat.chat_message import ChatMessage
from app.models.chat.chat_session import ChatSession


def create_chat_session(db: Session, title: str | None = None) -> ChatSession:
    session = ChatSession(title=title, is_active=True)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_chat_session(db: Session, session_id: UUID) -> ChatSession | None:
    stmt = select(ChatSession).where(ChatSession.id_session == session_id)
    return db.scalar(stmt)


def get_or_create_chat_session(
    db: Session,
    session_id: UUID | None = None,
    title: str | None = None,
) -> ChatSession:
    if session_id is not None:
        existing = get_chat_session(db, session_id)
        if existing is not None:
            return existing

    return create_chat_session(db=db, title=title)


def get_next_message_order(db: Session, session_id: UUID) -> int:
    stmt = select(func.max(ChatMessage.message_order)).where(
        ChatMessage.session_id == session_id
    )
    max_order = db.scalar(stmt)
    return 1 if max_order is None else max_order + 1


def save_chat_message(
    db: Session,
    session_id: UUID,
    role: str,
    content: str,
    sources_json: list[dict[str, Any]] | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        message_order=get_next_message_order(db, session_id),
        sources_json=sources_json,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_recent_messages(
    db: Session,
    session_id: UUID,
    limit: int = 6,
) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.message_order.desc())
        .limit(limit)
    )
    messages = list(db.scalars(stmt).all())
    messages.reverse()
    return messages


def clear_chat_session_messages(db: Session, session_id: UUID) -> None:
    stmt = select(ChatMessage).where(ChatMessage.session_id == session_id)
    messages = list(db.scalars(stmt).all())

    for message in messages:
        db.delete(message)

    db.commit()


def build_conversation_history(
    db: Session,
    session_id: UUID,
    limit: int = 6,
) -> list[dict[str, str]]:
    messages = get_recent_messages(db=db, session_id=session_id, limit=limit)

    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in messages
    ]