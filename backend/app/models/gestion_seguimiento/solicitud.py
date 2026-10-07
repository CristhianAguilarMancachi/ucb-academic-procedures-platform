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

    from app.models.gestion_seguimiento.tramite import (
        Tramite,
    )

    from app.models.gestion_seguimiento.solicitud_dato import (
        SolicitudDato,
    )

    from app.models.gestion_seguimiento.solicitud_requisito import (
        SolicitudRequisito,
    )


class Solicitud(Base):
    __tablename__ = "solicitud"

    # =========================================================
    # IDENTIFICACIÓN Y FLUJO
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

    id_etapa_actual: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    nombre_tramite_snapshot: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    tipo_finalizacion: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # =========================================================
    # DATOS DE CONTACTO DE ESTA SOLICITUD
    # =========================================================
    #
    # No modifican usuario ni usuario_correo.
    #
    # Son el contacto expresamente indicado por el solicitante
    # para esta solicitud.
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
        server_default=text("'borrador'"),
    )

    # =========================================================
    # FECHAS
    # =========================================================

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text(
            "CURRENT_TIMESTAMP"
        ),
    )

    fecha_envio: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text(
            "CURRENT_TIMESTAMP"
        ),
    )

    # =========================================================
    # RELACIONES
    # =========================================================

    solicitante: Mapped["Usuario"] = relationship(
        "Usuario",
        foreign_keys=[
            id_solicitante
        ],
    )

    tramite: Mapped["Tramite"] = relationship(
        "Tramite",
        foreign_keys=[
            id_tramite
        ],
    )

    datos: Mapped[list["SolicitudDato"]] = relationship(
        "SolicitudDato",
        back_populates="solicitud",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    requisitos: Mapped[
        list["SolicitudRequisito"]
    ] = relationship(
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
            estado <> 'en_proceso'
            OR id_etapa_actual IS NOT NULL
            """,
            name=(
                "ck_solicitud_proceso_etapa"
            ),
        ),

        ForeignKeyConstraint(
            [
                "id_solicitud",
                "id_etapa_actual",
            ],
            [
                "solicitud_etapa.id_solicitud",
                "solicitud_etapa.id_solicitud_etapa",
            ],
            name=(
                "fk_solicitud_etapa_actual"
            ),
            use_alter=True,
        ),

        CheckConstraint(
            """
            tipo_finalizacion IN (
                'entrega',
                'resultado_registrado',
                'externo'
            )
            """,
            name=(
                "ck_solicitud_tipo_finalizacion"
            ),
        ),

        CheckConstraint(
            """
            nombre_contacto IS NULL
            OR LENGTH(TRIM(nombre_contacto)) >= 2
            """,
            name=(
                "ck_solicitud_nombre_contacto"
            ),
        ),

        CheckConstraint(
            """
            telefono_contacto IS NULL
            OR LENGTH(TRIM(telefono_contacto)) >= 7
            """,
            name=(
                "ck_solicitud_telefono_contacto"
            ),
        ),

        CheckConstraint(
            """
            correo_contacto IS NULL
            OR LENGTH(TRIM(correo_contacto)) >= 5
            """,
            name=(
                "ck_solicitud_correo_contacto"
            ),
        ),

        CheckConstraint(
            """
            estado IN (
                'borrador',
                'pendiente_recepcion',
                'en_revision',
                'en_proceso',
                'lista_para_entrega',
                'finalizada',
                'cancelada',
                'rechazada'
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
            OR estado = 'cancelada'
            OR
            (
                estado NOT IN (
                    'borrador',
                    'cancelada'
                )
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
            name=(
                "ck_solicitud_fecha_envio_cronologia"
            ),
        ),

        Index(
            "idx_solicitud_etapa_actual",
            "id_etapa_actual",
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
            text(
                "fecha_creacion DESC"
            ),
        ),
    )

    # =========================================================
    # PROPIEDADES
    # =========================================================

    @property
    def es_borrador(
        self,
    ) -> bool:
        return (
            self.estado
            == "borrador"
        )

    @property
    def esta_enviada(
        self,
    ) -> bool:
        return (
            self.estado
            != "borrador"
            and self.fecha_envio
            is not None
        )