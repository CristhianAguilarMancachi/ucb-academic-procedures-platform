from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario
    from app.models.gestion_seguimiento.tramite import Tramite
    from app.models.gestion_seguimiento.solicitud_dato import SolicitudDato
    from app.models.gestion_seguimiento.solicitud_requisito import (
        SolicitudRequisito,
    )


class Solicitud(Base):
    __tablename__ = "solicitud"

    id_solicitud: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_solicitante: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            name="fk_solicitud_solicitante",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    id_tramite: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "tramite.id_tramite",
            name="fk_solicitud_tramite",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'borrador'"),
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    fecha_envio: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    solicitante: Mapped["Usuario"] = relationship(
        "Usuario",
        foreign_keys=[id_solicitante],
    )

    tramite: Mapped["Tramite"] = relationship(
        "Tramite",
        foreign_keys=[id_tramite],
    )

    datos: Mapped[list["SolicitudDato"]] = relationship(
        "SolicitudDato",
        back_populates="solicitud",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    requisitos: Mapped[list["SolicitudRequisito"]] = relationship(
        "SolicitudRequisito",
        back_populates="solicitud",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            """
            estado IN (
                'borrador',
                'pendiente_recepcion',
                'en_revision'
            )
            """,
            name="ck_solicitud_estado",
        ),
        CheckConstraint(
            """
            (
                estado = 'borrador'
                AND fecha_envio IS NULL
            )
            OR
            (
                estado <> 'borrador'
                AND fecha_envio IS NOT NULL
            )
            """,
            name="ck_solicitud_fecha_envio",
        ),
        CheckConstraint(
            """
            fecha_envio IS NULL
            OR fecha_envio >= fecha_creacion
            """,
            name="ck_solicitud_fecha_envio_cronologia",
        ),
        Index(
            "idx_solicitud_solicitante",
            "id_solicitante",
        ),
        Index(
            "idx_solicitud_tramite",
            "id_tramite",
        ),
        Index(
            "idx_solicitud_estado",
            "estado",
        ),
        Index(
            "idx_solicitud_solicitante_estado",
            "id_solicitante",
            "estado",
        ),
        Index(
            "idx_solicitud_fecha_creacion",
            text("fecha_creacion DESC"),
        ),
    )

    @property
    def es_borrador(self) -> bool:
        return self.estado == "borrador"

    @property
    def esta_enviada(self) -> bool:
        return (
            self.estado != "borrador"
            and self.fecha_envio is not None
        )