from __future__ import annotations

from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SolicitudObservacion(Base):
    __tablename__ = "solicitud_observacion"

    id_observacion: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_solicitud: Mapped[int] = mapped_column(BigInteger, ForeignKey("solicitud.id_solicitud", ondelete="RESTRICT"))
    id_solicitud_etapa: Mapped[int | None] = mapped_column(BigInteger)
    id_solicitud_requisito: Mapped[int | None] = mapped_column(BigInteger)
    id_usuario_observador: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuario.id_usuario", ondelete="RESTRICT"))
    detalle: Mapped[str] = mapped_column(Text)
    correccion_requerida: Mapped[str] = mapped_column(Text)
    canal_subsanacion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), server_default=text("'pendiente'"))
    fecha_observacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    id_usuario_resolucion: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id_usuario", ondelete="RESTRICT"))
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        ForeignKeyConstraint(["id_solicitud", "id_solicitud_etapa"], ["solicitud_etapa.id_solicitud", "solicitud_etapa.id_solicitud_etapa"], name="fk_observacion_etapa"),
        ForeignKeyConstraint(["id_solicitud", "id_solicitud_requisito"], ["solicitud_requisito.id_solicitud", "solicitud_requisito.id_solicitud_requisito"], name="fk_observacion_requisito"),
        CheckConstraint("length(trim(detalle)) > 0 AND length(trim(correccion_requerida)) > 0", name="ck_observacion_texto"),
        CheckConstraint("""(estado = 'pendiente' AND id_usuario_resolucion IS NULL AND fecha_resolucion IS NULL)
            OR (estado = 'resuelta' AND id_usuario_resolucion IS NOT NULL AND fecha_resolucion IS NOT NULL
            AND fecha_resolucion >= fecha_observacion)""", name="ck_observacion_resolucion"),
        Index("idx_solicitud_observacion_estado", "id_solicitud", "estado"),
    )
