from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.usuario_correo import UsuarioCorreo


class TokenVerificacionCorreo(Base):
    """
    Representa un token temporal utilizado para verificar
    la propiedad de un correo electrónico.

    El token original nunca se guarda en la base de datos.
    Solo se almacena su hash SHA-256.
    """

    __tablename__ = "token_verificacion_correo"

    id_token_verificacion: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_usuario_correo: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario_correo.id_usuario_correo",
            ondelete="CASCADE",
            name="fk_token_verificacion_correo",
        ),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_expiracion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    fecha_utilizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    fecha_revocacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    direccion_ip_solicitud: Mapped[str | None] = mapped_column(
        INET,
        nullable=True,
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    usuario_correo: Mapped[UsuarioCorreo] = relationship(
        "UsuarioCorreo",
        back_populates="tokens_verificacion",
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="uq_token_verificacion_hash",
        ),
        CheckConstraint(
            "fecha_expiracion > fecha_creacion",
            name="ck_token_verificacion_expiracion",
        ),
        CheckConstraint(
            """
            fecha_utilizacion IS NULL
            OR fecha_utilizacion >= fecha_creacion
            """,
            name="ck_token_verificacion_utilizacion",
        ),
        CheckConstraint(
            """
            fecha_revocacion IS NULL
            OR fecha_revocacion >= fecha_creacion
            """,
            name="ck_token_verificacion_revocacion",
        ),
        Index(
            "idx_token_verificacion_correo",
            "id_usuario_correo",
        ),
        Index(
            "idx_token_verificacion_expiracion",
            "fecha_expiracion",
            postgresql_where=text(
                """
                fecha_utilizacion IS NULL
                AND fecha_revocacion IS NULL
                """
            ),
        ),
    )

    @property
    def fue_utilizado(self) -> bool:
        return self.fecha_utilizacion is not None

    @property
    def esta_revocado(self) -> bool:
        return self.fecha_revocacion is not None

    @property
    def esta_expirado(self) -> bool:
        ahora = datetime.now(timezone.utc)
        return self.fecha_expiracion <= ahora

    @property
    def esta_disponible(self) -> bool:
        return (
            not self.fue_utilizado
            and not self.esta_revocado
            and not self.esta_expirado
        )

    def marcar_como_utilizado(
        self,
        fecha: datetime | None = None,
    ) -> None:
        self.fecha_utilizacion = fecha or datetime.now(timezone.utc)

    def revocar(
        self,
        fecha: datetime | None = None,
    ) -> None:
        self.fecha_revocacion = fecha or datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (
            "TokenVerificacionCorreo("
            f"id_token_verificacion={self.id_token_verificacion!r}, "
            f"id_usuario_correo={self.id_usuario_correo!r}, "
            f"fecha_expiracion={self.fecha_expiracion!r}, "
            f"fecha_utilizacion={self.fecha_utilizacion!r}, "
            f"fecha_revocacion={self.fecha_revocacion!r}"
            ")"
        )