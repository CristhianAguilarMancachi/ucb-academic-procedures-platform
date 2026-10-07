from __future__ import annotations

from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SolicitudEntrega(Base):
    __tablename__ = "solicitud_entrega"

    id_entrega: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_solicitud: Mapped[int] = mapped_column(BigInteger, ForeignKey("solicitud.id_solicitud", ondelete="RESTRICT"), unique=True)
    id_usuario_entrega: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuario.id_usuario", ondelete="RESTRICT"))
    receptor: Mapped[str] = mapped_column(String(10))
    nombre_receptor: Mapped[str | None] = mapped_column(String(200))
    documento_identidad: Mapped[str | None] = mapped_column(String(50))
    detalle: Mapped[str | None] = mapped_column(Text)
    fecha_entrega: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        CheckConstraint("receptor IN ('titular', 'tercero')"),
        CheckConstraint("receptor <> 'tercero' OR (nombre_receptor IS NOT NULL AND length(trim(nombre_receptor)) >= 2)", name="ck_entrega_receptor"),
    )
