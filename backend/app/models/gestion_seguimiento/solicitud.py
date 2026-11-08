
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario
    from app.models.gestion_seguimiento.tramite import Tramite
    from app.models.gestion_seguimiento.solicitud_dato import (
        SolicitudDato,
    )
    from app.models.gestion_seguimiento.solicitud_requisito import (
        SolicitudRequisito,
    )


class Solicitud(Base):
    __tablename__ = "solicitud"

    # =========================================================
    # IDENTIFICACIÓN
    # =========================================================

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

    # =========================================================
    # CONFIGURACIÓN CAPTURADA AL ENVIAR
    # =========================================================

    nombre_tramite_snapshot: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    tipo_finalizacion: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    tipo_intervencion: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ninguna",
        server_default=text("'ninguna'"),
    )

    # =========================================================
    # CONTACTO
    # =========================================================

    nombre_contacto: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    telefono_contacto: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    correo_contacto: Mapped[str | None] = mapped_column(
        String(254),
        nullable=True,
    )

    # =========================================================
    # ESTADO
    # =========================================================

    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # =========================================================
    # FECHAS
    # =========================================================

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

    # =========================================================
    # RELACIONES
    # =========================================================

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

    # =========================================================
    # RESTRICCIONES
    # =========================================================

    __table_args__ = (
        CheckConstraint(
            """
            estado = 'cancelada'
            OR fecha_envio IS NOT NULL
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
            "idx_solicitud_fecha_envio",
            "fecha_envio",
            "id_solicitud",
            postgresql_where=text(
                "fecha_envio IS NOT NULL"
            ),
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

    # =========================================================
    # PROPIEDADES
    # =========================================================

    @property
    def esta_enviada(self) -> bool:
        return self.fecha_envio is not None

    @property
    def requiere_intervencion(self) -> bool:
        return self.tipo_intervencion != "ninguna"
