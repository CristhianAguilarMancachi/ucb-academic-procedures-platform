from __future__ import annotations

from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SolicitudEtapa(Base):
    __tablename__ = "solicitud_etapa"

    id_solicitud_etapa: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_solicitud: Mapped[int] = mapped_column(BigInteger, ForeignKey("solicitud.id_solicitud", ondelete="CASCADE"))
    id_etapa_origen: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("tramite_etapa.id_etapa", ondelete="RESTRICT"))
    id_unidad: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidad_administrativa.id_unidad", ondelete="RESTRICT"))
    nombre: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(Text)
    orden: Mapped[int] = mapped_column(Integer)
    es_inicial: Mapped[bool] = mapped_column(Boolean)
    es_final: Mapped[bool] = mapped_column(Boolean)
    visible_solicitante: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    estado: Mapped[str] = mapped_column(String(20), server_default=text("'pendiente'"))
    id_usuario_inicio: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id_usuario", ondelete="RESTRICT"))
    id_usuario_finalizacion: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id_usuario", ondelete="RESTRICT"))
    fecha_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_finalizacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        Index("uq_solicitud_etapa_inicial", "id_solicitud", unique=True, postgresql_where=text("es_inicial = TRUE")),
        Index("uq_solicitud_etapa_final", "id_solicitud", unique=True, postgresql_where=text("es_final = TRUE")),
        UniqueConstraint("id_solicitud", "orden", name="uq_solicitud_etapa_orden"),
        UniqueConstraint("id_solicitud", "id_etapa_origen", name="uq_solicitud_etapa_origen"),
        UniqueConstraint("id_solicitud", "id_solicitud_etapa", name="uq_solicitud_etapa_pertenencia"),
        CheckConstraint("orden > 0"),
        CheckConstraint("estado IN ('pendiente', 'en_curso', 'completada')", name="ck_solicitud_etapa_estado"),
        CheckConstraint("""(estado = 'pendiente' AND fecha_inicio IS NULL AND fecha_finalizacion IS NULL
            AND id_usuario_inicio IS NULL AND id_usuario_finalizacion IS NULL)
            OR (estado = 'en_curso' AND fecha_inicio IS NOT NULL AND id_usuario_inicio IS NOT NULL
            AND fecha_finalizacion IS NULL AND id_usuario_finalizacion IS NULL)
            OR (estado = 'completada' AND fecha_inicio IS NOT NULL AND fecha_finalizacion IS NOT NULL
            AND id_usuario_inicio IS NOT NULL AND id_usuario_finalizacion IS NOT NULL
            AND fecha_finalizacion >= fecha_inicio)""", name="ck_solicitud_etapa_fechas"),
        CheckConstraint("fecha_inicio IS NULL OR fecha_inicio >= fecha_creacion", name="ck_solicitud_etapa_inicio"),
        Index("uq_solicitud_etapa_en_curso", "id_solicitud", unique=True, postgresql_where=text("estado = 'en_curso'")),
    )
