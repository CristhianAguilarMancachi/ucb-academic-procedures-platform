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
    from app.models.usuario import Usuario


class TokenRecuperacionContrasena(Base):
    """
    Representa un token temporal utilizado para restablecer
    la contraseña de una cuenta.

    El token original se envía al usuario, pero en PostgreSQL
    solo se guarda su hash SHA-256.
    """

    __tablename__ = "token_recuperacion_contrasena"

    id_token_recuperacion: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="CASCADE",
            name="fk_token_recuperacion_usuario",
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

    usuario: Mapped[Usuario] = relationship(
        "Usuario",
        back_populates="tokens_recuperacion",
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="uq_token_recuperacion_hash",
        ),
        CheckConstraint(
            "fecha_expiracion > fecha_creacion",
            name="ck_token_recuperacion_expiracion",
        ),
        CheckConstraint(
            """
            fecha_utilizacion IS NULL
            OR fecha_utilizacion >= fecha_creacion
            """,
            name="ck_token_recuperacion_utilizacion",
        ),
        CheckConstraint(
            """
            fecha_revocacion IS NULL
            OR fecha_revocacion >= fecha_creacion
            """,
            name="ck_token_recuperacion_revocacion",
        ),
        Index(
            "idx_token_recuperacion_usuario",
            "id_usuario",
        ),
        Index(
            "idx_token_recuperacion_expiracion",
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
            "TokenRecuperacionContrasena("
            f"id_token_recuperacion={self.id_token_recuperacion!r}, "
            f"id_usuario={self.id_usuario!r}, "
            f"fecha_expiracion={self.fecha_expiracion!r}, "
            f"fecha_utilizacion={self.fecha_utilizacion!r}, "
            f"fecha_revocacion={self.fecha_revocacion!r}"
            ")"
        )