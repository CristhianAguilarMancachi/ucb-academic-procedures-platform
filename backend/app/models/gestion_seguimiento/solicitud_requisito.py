from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.solicitud import Solicitud
    from app.models.gestion_seguimiento.tramite_requisito import (
        TramiteRequisito,
    )
    from app.models.gestion_seguimiento.tramite_requisito_economico import (
        TramiteRequisitoEconomico,
    )


class SolicitudRequisito(Base):
    __tablename__ = "solicitud_requisito"

    id_solicitud_requisito: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_solicitud: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "solicitud.id_solicitud",
            name="fk_solicitud_requisito_solicitud",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    id_requisito_origen: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "tramite_requisito.id_requisito",
            name="fk_solicitud_requisito_origen",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    obligatorio: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    orden: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    id_requisito_economico_origen: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "tramite_requisito_economico.id_requisito_economico",
            name="fk_solicitud_requisito_economico_origen",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    concepto_economico: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    monto_economico: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    moneda: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    gestion: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    codigo_concepto_externo: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    numero_factura: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    estado_verificacion: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pendiente'"),
    )

    id_usuario_verificador: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            name="fk_solicitud_requisito_usuario_verificador",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    fecha_verificacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    detalle_verificacion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
        back_populates="requisitos",
        foreign_keys=[id_solicitud],
    )

    requisito_origen: Mapped["TramiteRequisito | None"] = relationship(
        "TramiteRequisito",
        foreign_keys=[id_requisito_origen],
    )

    requisito_economico_origen: Mapped[
        "TramiteRequisitoEconomico | None"
    ] = relationship(
        "TramiteRequisitoEconomico",
        foreign_keys=[id_requisito_economico_origen],
    )

    __table_args__ = (
        UniqueConstraint(
            "id_solicitud",
            "id_requisito_origen",
            name="uq_solicitud_requisito_origen",
        ),
        CheckConstraint(
            "LENGTH(TRIM(nombre)) >= 2",
            name="ck_solicitud_requisito_nombre",
        ),
        CheckConstraint(
            "orden > 0",
            name="ck_solicitud_requisito_orden",
        ),
        CheckConstraint(
            """
            (
                concepto_economico IS NULL
                AND monto_economico IS NULL
                AND moneda IS NULL
                AND gestion IS NULL
                AND codigo_concepto_externo IS NULL
            )
            OR
            (
                concepto_economico IS NOT NULL
                AND monto_economico IS NOT NULL
                AND moneda IS NOT NULL
                AND gestion IS NOT NULL
            )
            """,
            name="ck_solicitud_requisito_economico",
        ),
        CheckConstraint(
            """
            concepto_economico IS NULL
            OR LENGTH(TRIM(concepto_economico)) >= 2
            """,
            name="ck_solicitud_requisito_concepto_economico",
        ),
        CheckConstraint(
            """
            monto_economico IS NULL
            OR monto_economico > 0
            """,
            name="ck_solicitud_requisito_monto_economico",
        ),
        CheckConstraint(
            """
            moneda IS NULL
            OR LENGTH(TRIM(moneda)) = 3
            """,
            name="ck_solicitud_requisito_moneda",
        ),
        CheckConstraint(
            """
            gestion IS NULL
            OR (
                gestion >= 2000
                AND gestion <= 2100
            )
            """,
            name="ck_solicitud_requisito_gestion",
        ),
        CheckConstraint(
            """
            numero_factura IS NULL
            OR LENGTH(TRIM(numero_factura)) >= 1
            """,
            name="ck_solicitud_requisito_numero_factura",
        ),
        CheckConstraint(
            """
            estado_verificacion IN (
                'pendiente',
                'cumple',
                'no_cumple'
            )
            """,
            name="ck_solicitud_requisito_estado_verificacion",
        ),
        CheckConstraint(
            """
            (
                estado_verificacion = 'pendiente'
                AND id_usuario_verificador IS NULL
                AND fecha_verificacion IS NULL
            )
            OR
            (
                estado_verificacion IN (
                    'cumple',
                    'no_cumple'
                )
                AND id_usuario_verificador IS NOT NULL
                AND fecha_verificacion IS NOT NULL
            )
            """,
            name="ck_solicitud_requisito_verificacion_consistente",
        ),
        CheckConstraint(
            """
            detalle_verificacion IS NULL
            OR LENGTH(TRIM(detalle_verificacion)) >= 1
            """,
            name="ck_solicitud_requisito_detalle_verificacion",
        ),
        Index(
            "idx_solicitud_requisito_solicitud",
            "id_solicitud",
        ),
        Index(
            "idx_solicitud_requisito_origen",
            "id_requisito_origen",
            postgresql_where=text(
                "id_requisito_origen IS NOT NULL"
            ),
        ),
        Index(
            "idx_solicitud_requisito_economico_origen",
            "id_requisito_economico_origen",
            postgresql_where=text(
                "id_requisito_economico_origen IS NOT NULL"
            ),
        ),
        Index(
            "idx_solicitud_requisito_numero_factura",
            "numero_factura",
            postgresql_where=text(
                "numero_factura IS NOT NULL"
            ),
        ),
        Index(
            "idx_solicitud_requisito_estado_verificacion",
            "id_solicitud",
            "estado_verificacion",
        ),
        Index(
            "idx_solicitud_requisito_usuario_verificador",
            "id_usuario_verificador",
            postgresql_where=text(
                "id_usuario_verificador IS NOT NULL"
            ),
        ),
    )

    @property
    def es_economico(self) -> bool:
        return self.concepto_economico is not None

    @property
    def esta_verificado(self) -> bool:
        return self.estado_verificacion == "cumple"