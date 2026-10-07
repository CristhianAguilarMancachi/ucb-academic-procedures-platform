from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.usuario import Usuario


class UsuarioIdentidadExterna(Base):
    """
    Vincula una cuenta interna del sistema con una identidad
    perteneciente a un proveedor externo de autenticación.

    Ejemplo:

        proveedor = "google"
        identificador_proveedor = valor del claim "sub"

    El correo del proveedor no se utiliza como identificador
    permanente de la identidad externa.
    """

    __tablename__ = "usuario_identidad_externa"

    # =========================================================
    # IDENTIFICADOR
    # =========================================================

    id_usuario_identidad: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    # =========================================================
    # USUARIO INTERNO
    # =========================================================

    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="CASCADE",
            name="fk_usuario_identidad_externa_usuario",
        ),
        nullable=False,
    )

    usuario: Mapped["Usuario"] = relationship(
        "Usuario",
        back_populates="identidades_externas",
    )

    # =========================================================
    # PROVEEDOR EXTERNO
    # =========================================================

    proveedor: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    identificador_proveedor: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # =========================================================
    # FECHAS
    # =========================================================

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # =========================================================
    # RESTRICCIONES
    # =========================================================

    __table_args__ = (
        UniqueConstraint(
            "proveedor",
            "identificador_proveedor",
            name="uq_identidad_externa_proveedor_identificador",
        ),

        UniqueConstraint(
            "id_usuario",
            "proveedor",
            name="uq_identidad_externa_usuario_proveedor",
        ),

        Index(
            "idx_identidad_externa_usuario",
            "id_usuario",
        ),

        Index(
            "idx_identidad_externa_proveedor",
            "proveedor",
        ),
    )

    def __repr__(self) -> str:
        return (
            "UsuarioIdentidadExterna("
            f"id_usuario_identidad={self.id_usuario_identidad!r}, "
            f"id_usuario={self.id_usuario!r}, "
            f"proveedor={self.proveedor!r}"
            ")"
        )