from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.tramite import Tramite
    from app.models.gestion_seguimiento.tramite_requisito_economico import (
        TramiteRequisitoEconomico,
    )


class TramiteRequisito(Base):
    """
    Representa un requisito asociado a un trámite.

    Los requisitos describen aquello que debe cumplir o presentar
    el solicitante. No representan etapas del proceso administrativo.
    """

    __tablename__ = "tramite_requisito"

    id_requisito: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_tramite: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "tramite.id_tramite",
            ondelete="CASCADE",
            name="fk_tramite_requisito_tramite",
        ),
        nullable=False,
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
        default=True,
        server_default=text("true"),
    )

    orden: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
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

    tramite: Mapped[Tramite] = relationship(
        "Tramite",
        back_populates="requisitos",
    )

    configuraciones_economicas: Mapped[
        list[TramiteRequisitoEconomico]
    ] = relationship(
        "TramiteRequisitoEconomico",
        back_populates="requisito",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        UniqueConstraint(
            "id_tramite",
            "nombre",
            name="uq_tramite_requisito_nombre",
        ),
        CheckConstraint(
            "LENGTH(TRIM(nombre)) >= 2",
            name="ck_tramite_requisito_nombre_no_vacio",
        ),
        CheckConstraint(
            "orden > 0",
            name="ck_tramite_requisito_orden",
        ),
        Index(
            "idx_tramite_requisito_tramite",
            "id_tramite",
        ),
        Index(
            "idx_tramite_requisito_tramite_activo",
            "id_tramite",
            "activo",
        ),
        Index(
            "idx_tramite_requisito_orden",
            "id_tramite",
            "orden",
        ),
    )

    @property
    def esta_activo(self) -> bool:
        """Indica si el requisito continúa vigente en el catálogo."""
        return self.activo

    @property
    def es_economico(self) -> bool:
        """
        Indica si el requisito tiene al menos una configuración
        económica asociada.

        Se calcula usando la relación cargada.
        """
        return bool(self.configuraciones_economicas)

    def __repr__(self) -> str:
        return (
            "TramiteRequisito("
            f"id_requisito={self.id_requisito!r}, "
            f"id_tramite={self.id_tramite!r}, "
            f"nombre={self.nombre!r}, "
            f"obligatorio={self.obligatorio!r}, "
            f"activo={self.activo!r}"
            ")"
        )