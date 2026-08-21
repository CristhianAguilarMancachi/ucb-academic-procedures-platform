from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.solicitud import Solicitud
    from app.models.usuario import Usuario


class SolicitudRecepcion(Base):
    __tablename__ = "solicitud_recepcion"

    __table_args__ = (
        UniqueConstraint(
            "id_solicitud",
            name="uq_solicitud_recepcion_solicitud",
        ),
        Index(
            "idx_solicitud_recepcion_usuario",
            "id_usuario_receptor",
        ),
        Index(
            "idx_solicitud_recepcion_fecha",
            "fecha_recepcion",
        ),
    )

    id_recepcion: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_solicitud: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "solicitud.id_solicitud",
            ondelete="RESTRICT",
            name="fk_solicitud_recepcion_solicitud",
        ),
        nullable=False,
    )

    id_usuario_receptor: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="RESTRICT",
            name="fk_solicitud_recepcion_usuario",
        ),
        nullable=False,
    )

    fecha_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    solicitud: Mapped["Solicitud"] = relationship(
        "Solicitud",
    )

    usuario_receptor: Mapped["Usuario"] = relationship(
        "Usuario",
    )