from __future__ import annotations

import uuid

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    UniqueConstraint,
    func,
)

from sqlalchemy.dialects.postgresql import (
    UUID,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


if TYPE_CHECKING:

    from app.models.chat.chat_message import (
        ChatMessage,
    )


class ChatMessageFeedback(Base):
    """
    Representa la valoración asignada por el usuario
    a una respuesta concreta del asistente RAG.

    rating:
        1  -> respuesta útil
       -1  -> respuesta no útil

    Cada mensaje del asistente puede tener como máximo
    una valoración activa.
    """

    __tablename__ = (
        "chat_message_feedback"
    )


    id_feedback: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(
            as_uuid=True,
        ),
        primary_key=True,
        default=uuid.uuid4,
    )


    message_id: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(
            as_uuid=True,
        ),
        ForeignKey(
            "chat_message.id_message",
            ondelete="CASCADE",
            name=(
                "fk_chat_message_feedback_"
                "message"
            ),
        ),
        nullable=False,
    )


    rating: Mapped[
        int
    ] = mapped_column(
        SmallInteger,
        nullable=False,
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


    updated_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


    # =====================================================
    # RELACIONES
    # =====================================================

    message: Mapped[
        "ChatMessage"
    ] = relationship(
        "ChatMessage",
        back_populates="feedback",
    )


    # =====================================================
    # RESTRICCIONES
    # =====================================================

    __table_args__ = (

        UniqueConstraint(
            "message_id",
            name=(
                "uq_chat_message_feedback_"
                "message"
            ),
        ),

        CheckConstraint(
            "rating IN (-1, 1)",
            name=(
                "ck_chat_message_feedback_"
                "rating"
            ),
        ),
    )


    def __repr__(
        self,
    ) -> str:

        return (
            "ChatMessageFeedback("
            f"id_feedback={self.id_feedback!r}, "
            f"message_id={self.message_id!r}, "
            f"rating={self.rating!r}"
            ")"
        )