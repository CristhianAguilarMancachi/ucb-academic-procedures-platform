
from datetime import date

from sqlalchemy import (
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class VersionDocumento(Base):
    __tablename__ = "version_documento"

    vigente_desde: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    vigente_hasta: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "vigente_hasta IS NULL OR "
            "(vigente_desde IS NOT NULL "
            "AND vigente_hasta >= vigente_desde)",
            name="ck_version_documento_vigencia",
        ),
    )

    id_version_documento: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    id_documento_institucional: Mapped[int] = mapped_column(
        ForeignKey(
            "documento_institucional.id_documento_institucional"
        ),
        nullable=False,
    )

    numero_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    fecha_version: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    hash_archivo: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="activo",
    )

    observacion: Mapped[str | None] = mapped_column(Text)

    fecha_creacion: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    documento = relationship(
        "DocumentoInstitucional",
        back_populates="versiones",
        foreign_keys=[id_documento_institucional],
    )

    chunks = relationship(
        "ChunkDocumento",
        back_populates="version_documento",
    )
