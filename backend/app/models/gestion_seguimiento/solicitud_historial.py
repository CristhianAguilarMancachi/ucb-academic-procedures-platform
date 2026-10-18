from __future__ import annotations

from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SolicitudHistorial(Base):
    __tablename__ = "solicitud_historial"

    id_historial: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_solicitud: Mapped[int] = mapped_column(BigInteger, ForeignKey("solicitud.id_solicitud", ondelete="CASCADE"))
    id_usuario_actor: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id_usuario", ondelete="SET NULL"))
    id_solicitud_requisito: Mapped[int | None] = mapped_column(BigInteger)
    evento: Mapped[str] = mapped_column(String(80))
    detalle: Mapped[str] = mapped_column(Text)
    visible_solicitante: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    fecha_evento: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        ForeignKeyConstraint(["id_solicitud", "id_solicitud_requisito"], ["solicitud_requisito.id_solicitud", "solicitud_requisito.id_solicitud_requisito"], name="fk_historial_requisito"),
        CheckConstraint("length(trim(evento)) > 0 AND length(trim(detalle)) > 0", name="ck_solicitud_historial_texto"),
        Index("idx_solicitud_historial_cronologia", "id_solicitud", "fecha_evento", "id_historial"),
    )
