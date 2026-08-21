from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.solicitud import Solicitud
    from app.models.gestion_seguimiento.tramite_campo import TramiteCampo


class SolicitudDato(Base):
    __tablename__ = "solicitud_dato"

    id_solicitud_dato: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_solicitud: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "solicitud.id_solicitud",
            name="fk_solicitud_dato_solicitud",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    id_campo: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "tramite_campo.id_campo",
            name="fk_solicitud_dato_campo",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    valor: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    solicitud: Mapped["Solicitud"] = relationship(
        "Solicitud",
        back_populates="datos",
        foreign_keys=[id_solicitud],
    )

    campo: Mapped["TramiteCampo"] = relationship(
        "TramiteCampo",
        foreign_keys=[id_campo],
    )

    __table_args__ = (
        UniqueConstraint(
            "id_solicitud",
            "id_campo",
            name="uq_solicitud_dato_campo",
        ),
        CheckConstraint(
            "valor <> 'null'::jsonb",
            name="ck_solicitud_dato_valor",
        ),
        Index(
            "idx_solicitud_dato_solicitud",
            "id_solicitud",
        ),
        Index(
            "idx_solicitud_dato_campo",
            "id_campo",
        ),
    )