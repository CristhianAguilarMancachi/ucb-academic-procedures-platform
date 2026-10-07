from __future__ import annotations

from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SolicitudResultado(Base):
    __tablename__ = "solicitud_resultado"

    id_resultado: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_solicitud: Mapped[int] = mapped_column(BigInteger, ForeignKey("solicitud.id_solicitud", ondelete="RESTRICT"), unique=True)
    tipo_finalizacion: Mapped[str] = mapped_column(String(30))
    detalle: Mapped[str | None] = mapped_column(Text)
    id_usuario_registro: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuario.id_usuario", ondelete="RESTRICT"))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (CheckConstraint("tipo_finalizacion IN ('entrega', 'resultado_registrado', 'externo')"),)
