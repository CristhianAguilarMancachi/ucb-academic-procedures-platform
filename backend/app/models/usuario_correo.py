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
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.token_verificacion_correo import (
        TokenVerificacionCorreo,
    )
    from app.models.usuario import Usuario


class UsuarioCorreo(Base):
    """
    Representa un correo asociado a una cuenta.

    Una cuenta puede tener correo institucional, correo personal
    o ambos. Solo un correo activo puede ser principal.
    """

    __tablename__ = "usuario_correo"

    id_usuario_correo: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="CASCADE",
            name="fk_usuario_correo_usuario",
        ),
        nullable=False,
    )

    correo: Mapped[str] = mapped_column(
        CITEXT,
        nullable=False,
        unique=True,
    )

    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    es_principal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    verificado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    fecha_verificacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    usuario: Mapped[Usuario] = relationship(
        "Usuario",
        back_populates="correos",
    )

    tokens_verificacion: Mapped[
        list[TokenVerificacionCorreo]
    ] = relationship(
        "TokenVerificacionCorreo",
        back_populates="usuario_correo",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('institucional', 'personal')",
            name="ck_usuario_correo_tipo",
        ),
        CheckConstraint(
            """
            (
                verificado = FALSE
                AND fecha_verificacion IS NULL
            )
            OR
            (
                verificado = TRUE
                AND fecha_verificacion IS NOT NULL
            )
            """,
            name="ck_usuario_correo_verificacion",
        ),
        Index(
            "idx_usuario_correo_usuario",
            "id_usuario",
        ),
        Index(
            "idx_usuario_correo_busqueda",
            "correo",
        ),
        Index(
            "uq_usuario_correo_principal_activo",
            "id_usuario",
            unique=True,
            postgresql_where=text(
                "es_principal = TRUE AND activo = TRUE"
            ),
        ),
    )

    @property
    def puede_iniciar_sesion(self) -> bool:
        """
        Indica si el correo puede utilizarse para iniciar sesión.
        """
        return self.activo and self.verificado

    @property
    def es_institucional(self) -> bool:
        return self.tipo == "institucional"

    def __repr__(self) -> str:
        return (
            "UsuarioCorreo("
            f"id_usuario_correo={self.id_usuario_correo!r}, "
            f"correo={self.correo!r}, "
            f"tipo={self.tipo!r}, "
            f"verificado={self.verificado!r}, "
            f"activo={self.activo!r}"
            ")"
        )