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
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.tramite_requisito import (
        TramiteRequisito,
    )


class TramiteRequisitoEconomico(Base):
    """
    Representa la configuración económica asociada a un requisito
    de un trámite.

    Esta tabla define el concepto y monto esperado para una gestión
    determinada. No registra pagos realizados por los usuarios ni
    ejecuta validaciones contra servicios externos.

    El campo codigo_concepto_externo queda preparado para relacionar
    posteriormente el concepto del sistema con el identificador que
    utilice una API externa de validación de pagos.
    """

    __tablename__ = "tramite_requisito_economico"

    id_requisito_economico: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_requisito: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "tramite_requisito.id_requisito",
            ondelete="CASCADE",
            name="fk_tramite_requisito_economico_requisito",
        ),
        nullable=False,
    )

    concepto: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    monto: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    moneda: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="BOB",
        server_default=text("'BOB'"),
    )

    gestion: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    codigo_concepto_externo: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    requisito: Mapped[TramiteRequisito] = relationship(
        "TramiteRequisito",
        back_populates="configuraciones_economicas",
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        UniqueConstraint(
            "id_requisito",
            "gestion",
            name="uq_tramite_requisito_economico_gestion",
        ),
        CheckConstraint(
            "LENGTH(TRIM(concepto)) >= 2",
            name="ck_tramite_requisito_economico_concepto",
        ),
        CheckConstraint(
            "monto > 0",
            name="ck_tramite_requisito_economico_monto",
        ),
        CheckConstraint(
            "LENGTH(TRIM(moneda)) = 3",
            name="ck_tramite_requisito_economico_moneda",
        ),
        CheckConstraint(
            """
            gestion >= 2000
            AND gestion <= 2100
            """,
            name="ck_tramite_requisito_economico_gestion",
        ),
        Index(
            "idx_tramite_requisito_economico_requisito",
            "id_requisito",
        ),
        Index(
            "idx_tramite_requisito_economico_gestion",
            "gestion",
            "activo",
        ),
        Index(
            "idx_tramite_requisito_economico_codigo_externo",
            "codigo_concepto_externo",
            postgresql_where=text(
                "codigo_concepto_externo IS NOT NULL"
            ),
        ),
    )

    @property
    def esta_activo(self) -> bool:
        """Indica si esta configuración económica está vigente."""
        return self.activo

    def __repr__(self) -> str:
        return (
            "TramiteRequisitoEconomico("
            f"id_requisito_economico={self.id_requisito_economico!r}, "
            f"id_requisito={self.id_requisito!r}, "
            f"concepto={self.concepto!r}, "
            f"monto={self.monto!r}, "
            f"moneda={self.moneda!r}, "
            f"gestion={self.gestion!r}, "
            f"activo={self.activo!r}"
            ")"
        )