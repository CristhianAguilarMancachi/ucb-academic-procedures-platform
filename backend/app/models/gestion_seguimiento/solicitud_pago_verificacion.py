from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.solicitud_requisito import (
        SolicitudRequisito,
    )
    from app.models.usuario import Usuario


class SolicitudPagoVerificacion(Base):
    __tablename__ = "solicitud_pago_verificacion"

    __table_args__ = (
        CheckConstraint(
            "estado IN ('verificado', 'no_verificado', 'error')",
            name="ck_pago_verificacion_estado",
        ),
        CheckConstraint(
            "LENGTH(TRIM(numero_factura_consultado)) >= 1",
            name="ck_pago_verificacion_numero_factura",
        ),
        CheckConstraint(
            "LENGTH(TRIM(codigo_concepto_consultado)) >= 1",
            name="ck_pago_verificacion_codigo_consultado",
        ),
        CheckConstraint(
            """
            codigo_concepto_reportado IS NULL
            OR LENGTH(TRIM(codigo_concepto_reportado)) >= 1
            """,
            name="ck_pago_verificacion_codigo_reportado",
        ),
        CheckConstraint(
            """
            estado_factura_reportado IS NULL
            OR LENGTH(TRIM(estado_factura_reportado)) >= 1
            """,
            name="ck_pago_verificacion_estado_factura_reportado",
        ),
        CheckConstraint(
            "monto_reportado IS NULL OR monto_reportado > 0",
            name="ck_pago_verificacion_monto",
        ),
        CheckConstraint(
            """
            moneda_reportada IS NULL
            OR LENGTH(TRIM(moneda_reportada)) = 3
            """,
            name="ck_pago_verificacion_moneda",
        ),
        Index(
            "idx_pago_verificacion_requisito",
            "id_solicitud_requisito",
        ),
        Index(
            "idx_pago_verificacion_usuario",
            "id_usuario_verificador",
        ),
        Index(
            "idx_pago_verificacion_estado",
            "estado",
        ),
        Index(
            "idx_pago_verificacion_fecha",
            "fecha_verificacion",
        ),
        Index(
            "idx_pago_verificacion_numero_factura",
            "numero_factura_consultado",
        ),
        Index(
            "idx_pago_verificacion_codigo_consultado",
            "codigo_concepto_consultado",
        ),
        Index(
            "uq_pago_verificacion_factura_verificada",
            "numero_factura_consultado",
            unique=True,
            postgresql_where=text("estado = 'verificado'"),
        ),
    )

    id_verificacion_pago: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_solicitud_requisito: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "solicitud_requisito.id_solicitud_requisito",
            ondelete="RESTRICT",
            name="fk_pago_verificacion_solicitud_requisito",
        ),
        nullable=False,
    )

    id_usuario_verificador: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="RESTRICT",
            name="fk_pago_verificacion_usuario",
        ),
        nullable=False,
    )

    numero_factura_consultado: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    codigo_concepto_consultado: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    codigo_concepto_reportado: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    estado_factura_reportado: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    monto_reportado: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    moneda_reportada: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    detalle_respuesta: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    fecha_verificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    )

    solicitud_requisito: Mapped["SolicitudRequisito"] = relationship(
        "SolicitudRequisito",
    )

    usuario_verificador: Mapped["Usuario"] = relationship(
        "Usuario",
    )