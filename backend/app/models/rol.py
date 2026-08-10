from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario
    from app.models.usuario_rol import UsuarioRol


class Rol(Base):
    """
    Define un grupo general de permisos dentro del sistema.

    Los roles iniciales son:
    - solicitante
    - personal_administrativo
    - administrador
    """

    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(50),
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

    asignaciones: Mapped[list[UsuarioRol]] = relationship(
        "UsuarioRol",
        back_populates="rol",
    )

    usuarios: Mapped[list[Usuario]] = relationship(
        "Usuario",
        secondary="usuario_rol",
        primaryjoin="Rol.id_rol == UsuarioRol.id_rol",
        secondaryjoin="Usuario.id_usuario == UsuarioRol.id_usuario",
        viewonly=True,
    )

    # =====================================================
    # RESTRICCIONES
    # =====================================================

    __table_args__ = (
        CheckConstraint(
            "LENGTH(TRIM(nombre)) >= 3",
            name="ck_rol_nombre_no_vacio",
        ),
    )

    @property
    def nombre_normalizado(self) -> str:
        return self.nombre.strip().lower()

    def __repr__(self) -> str:
        return (
            "Rol("
            f"id_rol={self.id_rol!r}, "
            f"nombre={self.nombre!r}, "
            f"activo={self.activo!r}"
            ")"
        )