from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.unidad_administrativa import (
        UnidadAdministrativa,
    )
    from app.models.usuario import Usuario


class UsuarioUnidad(Base):
    """
    Representa la asociación de un usuario con una unidad administrativa.

    Esta relación es independiente de los roles del usuario.

    Por ejemplo, un usuario puede tener el rol
    'personal_administrativo' mediante usuario_rol y, adicionalmente,
    estar asociado a una unidad mediante usuario_unidad.
    """

    __tablename__ = "usuario_unidad"

    id_usuario_unidad: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="CASCADE",
            name="fk_usuario_unidad_usuario",
        ),
        nullable=False,
    )

    id_unidad: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "unidad_administrativa.id_unidad",
            ondelete="RESTRICT",
            name="fk_usuario_unidad_unidad",
        ),
        nullable=False,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    asignado_por: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="SET NULL",
            name="fk_usuario_unidad_asignado_por",
        ),
        nullable=True,
    )

    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_revocacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    usuario: Mapped[Usuario] = relationship(
        "Usuario",
        foreign_keys=[id_usuario],
    )

    unidad: Mapped[UnidadAdministrativa] = relationship(
        "UnidadAdministrativa",
        back_populates="asignaciones_usuario",
    )

    usuario_asignador: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[asignado_por],
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        UniqueConstraint(
            "id_usuario",
            "id_unidad",
            name="uq_usuario_unidad",
        ),
        CheckConstraint(
            """
            (
                activo = TRUE
                AND fecha_revocacion IS NULL
            )
            OR
            (
                activo = FALSE
            )
            """,
            name="ck_usuario_unidad_revocacion",
        ),
        Index(
            "idx_usuario_unidad_usuario",
            "id_usuario",
        ),
        Index(
            "idx_usuario_unidad_unidad",
            "id_unidad",
        ),
        Index(
            "idx_usuario_unidad_activo",
            "id_unidad",
            "activo",
        ),
    )

    @property
    def esta_vigente(self) -> bool:
        """Indica si la asociación usuario-unidad continúa vigente."""
        return self.activo and self.fecha_revocacion is None

    def revocar(
        self,
        fecha: datetime | None = None,
    ) -> None:
        """Revoca la asociación sin eliminar su registro histórico."""
        self.activo = False
        self.fecha_revocacion = fecha or datetime.now(timezone.utc)

    def reactivar(self) -> None:
        """Reactiva una asociación previamente revocada."""
        self.activo = True
        self.fecha_revocacion = None

    def __repr__(self) -> str:
        return (
            "UsuarioUnidad("
            f"id_usuario_unidad={self.id_usuario_unidad!r}, "
            f"id_usuario={self.id_usuario!r}, "
            f"id_unidad={self.id_unidad!r}, "
            f"activo={self.activo!r}"
            ")"
        )