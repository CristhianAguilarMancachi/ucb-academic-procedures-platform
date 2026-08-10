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
    from app.models.rol import Rol
    from app.models.usuario import Usuario


class UsuarioRol(Base):
    """
    Representa la asignación de un rol a un usuario.

    Una cuenta puede tener uno o varios roles.
    """

    __tablename__ = "usuario_rol"

    id_usuario_rol: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="CASCADE",
            name="fk_usuario_rol_usuario",
        ),
        nullable=False,
    )

    id_rol: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "rol.id_rol",
            name="fk_usuario_rol_rol",
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
            name="fk_usuario_rol_asignado_por",
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

    usuario: Mapped[Usuario] = relationship(
        "Usuario",
        foreign_keys=[id_usuario],
        back_populates="asignaciones_rol",
    )

    rol: Mapped[Rol] = relationship(
        "Rol",
        back_populates="asignaciones",
    )

    usuario_asignador: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[asignado_por],
        back_populates="asignaciones_rol_realizadas",
    )

    __table_args__ = (
        UniqueConstraint(
            "id_usuario",
            "id_rol",
            name="uq_usuario_rol",
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
            name="ck_usuario_rol_revocacion",
        ),
        Index(
            "idx_usuario_rol_usuario",
            "id_usuario",
        ),
        Index(
            "idx_usuario_rol_rol",
            "id_rol",
        ),
        Index(
            "idx_usuario_rol_activo",
            "id_usuario",
            "activo",
        ),
    )

    @property
    def esta_vigente(self) -> bool:
        return self.activo and self.fecha_revocacion is None

    def revocar(
        self,
        fecha: datetime | None = None,
    ) -> None:
        self.activo = False
        self.fecha_revocacion = fecha or datetime.now(timezone.utc)

    def reactivar(self) -> None:
        self.activo = True
        self.fecha_revocacion = None

    def __repr__(self) -> str:
        return (
            "UsuarioRol("
            f"id_usuario_rol={self.id_usuario_rol!r}, "
            f"id_usuario={self.id_usuario!r}, "
            f"id_rol={self.id_rol!r}, "
            f"activo={self.activo!r}"
            ")"
        )