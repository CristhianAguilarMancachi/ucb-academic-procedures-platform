
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.solicitud import Solicitud
    from app.models.gestion_seguimiento.solicitud_intervencion import (
        SolicitudIntervencion,
    )


class SolicitudNotificacion(Base):
    """
    Registro persistente de las notificaciones
    relacionadas con una solicitud.

    Tipos:
        convocatoria: aviso para revisión o firma.
        resultado: aviso del resultado del trámite.

    Estados:
        pendiente: aún no enviado.
        enviado: servicio de correo aceptó el envío.
        fallido: ocurrió un error.

    Los reintentos actualizan el mismo registro.
    """

    __tablename__ = "solicitud_notificacion"

    # =====================================================
    # IDENTIFICACIÓN
    # =====================================================

    id_notificacion: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )

    id_solicitud: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "solicitud.id_solicitud",
            name="fk_notificacion_solicitud",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    id_intervencion: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "solicitud_intervencion.id_intervencion",
            name="fk_notificacion_intervencion",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    # =====================================================
    # CLASIFICACIÓN Y ESTADO
    # =====================================================

    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pendiente",
        server_default=text("'pendiente'"),
    )

    # =====================================================
    # CONTENIDO
    # =====================================================

    destinatario: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
    )

    asunto: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    contenido_texto: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # =====================================================
    # CONTROL DE ENVÍO
    # =====================================================

    intentos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    fecha_ultimo_intento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    fecha_envio: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ultimo_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    referencia_externa: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    solicitud: Mapped["Solicitud"] = relationship(
        "Solicitud",
        foreign_keys=[id_solicitud],
    )

    intervencion: Mapped["SolicitudIntervencion | None"] = (
        relationship(
            "SolicitudIntervencion",
            foreign_keys=[id_intervencion],
        )
    )

    # =====================================================
    # RESTRICCIONES
    # =====================================================

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('convocatoria', 'resultado')",
            name="ck_notificacion_tipo",
        ),
        CheckConstraint(
            """
            (
                tipo = 'convocatoria'
                AND id_intervencion IS NOT NULL
            )
            OR
            (
                tipo = 'resultado'
                AND id_intervencion IS NULL
            )
            """,
            name="ck_notificacion_tipo_intervencion",
        ),
        CheckConstraint(
            """
            estado IN (
                'pendiente',
                'enviado',
                'fallido'
            )
            """,
            name="ck_notificacion_estado",
        ),
        CheckConstraint(
            "intentos >= 0",
            name="ck_notificacion_intentos",
        ),
        CheckConstraint(
            """
            LENGTH(TRIM(destinatario)) > 0
            AND LENGTH(TRIM(asunto)) > 0
            AND LENGTH(TRIM(contenido_texto)) > 0
            """,
            name="ck_notificacion_texto",
        ),
        CheckConstraint(
            """
            (
                estado = 'enviado'
                AND fecha_envio IS NOT NULL
            )
            OR
            (
                estado <> 'enviado'
                AND fecha_envio IS NULL
            )
            """,
            name="ck_notificacion_fecha_envio",
        ),
        Index(
            "idx_notificacion_solicitud",
            "id_solicitud",
            text("fecha_creacion DESC"),
        ),
        Index(
            "idx_notificacion_estado",
            "estado",
        ),
        Index(
            "uq_notificacion_convocatoria",
            "id_intervencion",
            unique=True,
            postgresql_where=text(
                "tipo = 'convocatoria'"
            ),
        ),
        Index(
            "uq_notificacion_resultado",
            "id_solicitud",
            unique=True,
            postgresql_where=text(
                "tipo = 'resultado'"
            ),
        ),
    )

    # =====================================================
    # PROPIEDADES
    # =====================================================

    @property
    def fue_enviada(self) -> bool:
        return self.estado == "enviado"

    @property
    def puede_reintentarse(self) -> bool:
        return self.estado == "fallido"

    def __repr__(self) -> str:
        return (
            "SolicitudNotificacion("
            f"id_notificacion={self.id_notificacion!r}, "
            f"id_solicitud={self.id_solicitud!r}, "
            f"tipo={self.tipo!r}, "
            f"estado={self.estado!r}, "
            f"intentos={self.intentos!r}"
            ")"
        )
