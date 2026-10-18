from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.usuario_unidad import UsuarioUnidad


class UnidadAdministrativa(Base):
    """
    Representa una unidad administrativa que puede participar
    en la gestión de trámites académicos.

    La existencia de una unidad no implica que participe en un
    trámite concreto ni define el orden de un proceso.
    """

    __tablename__ = "unidad_administrativa"

    id_unidad: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
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

    asignaciones_usuario: Mapped[list[UsuarioUnidad]] = relationship(
        "UsuarioUnidad",
        back_populates="unidad",
        passive_deletes=True,
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        CheckConstraint(
            "LENGTH(TRIM(nombre)) >= 3",
            name="ck_unidad_administrativa_nombre_no_vacio",
        ),
        Index(
            "idx_unidad_administrativa_activo",
            "activo",
        ),
    )

    @property
    def esta_activa(self) -> bool:
        """Indica si la unidad se encuentra habilitada."""
        return self.activo

    def __repr__(self) -> str:
        return (
            "UnidadAdministrativa("
            f"id_unidad={self.id_unidad!r}, "
            f"nombre={self.nombre!r}, "
            f"activo={self.activo!r}"
            ")"
        )