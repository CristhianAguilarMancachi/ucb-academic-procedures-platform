from __future__ import annotations

import uuid

from datetime import datetime
from typing import (
    Any,
    TYPE_CHECKING,
)

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


if TYPE_CHECKING:

    from app.models.chat.chat_message_feedback import (
        ChatMessageFeedback,
    )

    from app.models.chat.chat_session import (
        ChatSession,
    )


class ChatMessage(Base):

    __tablename__ = "chat_message"


    id_message: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(
            as_uuid=True,
        ),
        primary_key=True,
        default=uuid.uuid4,
    )


    session_id: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(
            as_uuid=True,
        ),
        ForeignKey(
            "chat_session.id_session",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    role: Mapped[
        str
    ] = mapped_column(
        String(20),
        nullable=False,
    )


    content: Mapped[
        str
    ] = mapped_column(
        Text,
        nullable=False,
    )


    message_order: Mapped[
        int
    ] = mapped_column(
        Integer,
        nullable=False,
    )


    sources_json: Mapped[
        list[
            dict[
                str,
                Any,
            ]
        ]
        | None
    ] = mapped_column(
        JSONB,
        nullable=True,
    )


    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=False,
        server_default=func.now(),
    )


    # =====================================================
    # RELACIONES
    # =====================================================

    session: Mapped[
        "ChatSession"
    ] = relationship(
        "ChatSession",
        back_populates="messages",
    )


    feedback: Mapped[
        "ChatMessageFeedback | None"
    ] = relationship(
        "ChatMessageFeedback",
        back_populates="message",
        uselist=False,
        cascade=(
            "all, delete-orphan"
        ),
    )