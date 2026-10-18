
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
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
    from app.models.usuario import Usuario
    from app.models.gestion_seguimiento.solicitud import Solicitud


class SolicitudIntervencion(Base):
    """
    Registra una intervención presencial necesaria para
    continuar o finalizar una solicitud.

    Tipos:
        conformidad: revisión de una propuesta académica.
        firma: firma presencial del estudiante.

    Una solicitud puede tener varias intervenciones
    históricas, pero solo una convocatoria abierta.

    Las actividades administrativas internas no
    se registran como intervenciones.
    """

    __tablename__ = "solicitud_intervencion"

    # =====================================================
    # IDENTIFICACIÓN
    # =====================================================

    id_intervencion: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )

    id_solicitud: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "solicitud.id_solicitud",
            name="fk_intervencion_solicitud",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    # =====================================================
    # TIPO Y ESTADO
    # =====================================================

    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="convocada",
        server_default=text("'convocada'"),
    )

    # =====================================================
    # CONVOCATORIA
    # =====================================================

    id_usuario_convocatoria: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            name="fk_intervencion_usuario_convocatoria",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    fecha_convocatoria: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # =====================================================
    # RESULTADO PRESENCIAL
    # =====================================================

    fecha_revision: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    id_usuario_registro: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            name="fk_intervencion_usuario_registro",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    fecha_registro: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    motivo_desacuerdo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    solicitud: Mapped["Solicitud"] = relationship(
        "Solicitud",
        foreign_keys=[id_solicitud],
    )

    usuario_convocatoria: Mapped["Usuario"] = relationship(
        "Usuario",
        foreign_keys=[id_usuario_convocatoria],
    )

    usuario_registro: Mapped["Usuario | None"] = relationship(
        "Usuario",
        foreign_keys=[id_usuario_registro],
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        CheckConstraint(
            """
            (
                tipo = 'conformidad'
                AND estado IN (
                    'convocada',
                    'conforme',
                    'no_conforme',
                    'anulada'
                )
            )
            OR
            (
                tipo = 'firma'
                AND estado IN (
                    'convocada',
                    'firmada',
                    'anulada'
                )
            )
            """,
            name="ck_intervencion_tipo_estado",
        ),
        CheckConstraint(
            """
            (
                estado = 'convocada'
                AND fecha_revision IS NULL
                AND id_usuario_registro IS NULL
                AND fecha_registro IS NULL
            )
            OR
            (
                estado IN (
                    'conforme',
                    'no_conforme',
                    'firmada'
                )
                AND fecha_revision IS NOT NULL
                AND id_usuario_registro IS NOT NULL
                AND fecha_registro IS NOT NULL
            )
            OR
            (
                estado = 'anulada'
                AND fecha_revision IS NULL
                AND id_usuario_registro IS NOT NULL
                AND fecha_registro IS NOT NULL
            )
            """,
            name="ck_intervencion_registro",
        ),
        CheckConstraint(
            """
            (
                estado = 'no_conforme'
                AND motivo_desacuerdo IS NOT NULL
                AND LENGTH(TRIM(motivo_desacuerdo)) > 0
            )
            OR
            (
                estado <> 'no_conforme'
                AND motivo_desacuerdo IS NULL
            )
            """,
            name="ck_intervencion_motivo",
        ),
        CheckConstraint(
            """
            fecha_registro IS NULL
            OR fecha_registro >= fecha_convocatoria
            """,
            name="ck_intervencion_fecha_registro",
        ),
        Index(
            "idx_intervencion_solicitud",
            "id_solicitud",
            text("fecha_convocatoria DESC"),
        ),
        Index(
            "uq_intervencion_convocatoria_abierta",
            "id_solicitud",
            unique=True,
            postgresql_where=text(
                "estado = 'convocada'"
            ),
        ),
    )

    # =====================================================
    # PROPIEDADES
    # =====================================================

    @property
    def pendiente(self) -> bool:
        return self.estado == "convocada"

    @property
    def completada(self) -> bool:
        return (
            (self.tipo == "conformidad" and self.estado == "conforme")
            or (self.tipo == "firma" and self.estado == "firmada")
        )

    @property
    def requiere_nueva_revision(self) -> bool:
        return (
            self.tipo == "conformidad"
            and self.estado == "no_conforme"
        )

    def __repr__(self) -> str:
        return (
            "SolicitudIntervencion("
            f"id_intervencion={self.id_intervencion!r}, "
            f"id_solicitud={self.id_solicitud!r}, "
            f"tipo={self.tipo!r}, "
            f"estado={self.estado!r}"
            ")"
        )
