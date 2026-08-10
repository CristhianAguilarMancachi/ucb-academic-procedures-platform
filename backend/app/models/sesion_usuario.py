from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class SesionUsuario(Base):
    """
    Representa una sesión autenticada de un usuario.

    El refresh token original no se guarda en PostgreSQL.
    Únicamente se almacena su hash SHA-256 para poder
    identificar, rotar y revocar la sesión.
    """

    __tablename__ = "sesion_usuario"

    id_sesion: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="CASCADE",
            name="fk_sesion_usuario",
        ),
        nullable=False,
    )

    identificador_sesion: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )

    refresh_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_ultima_actividad: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_expiracion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    fecha_revocacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    motivo_revocacion: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    direccion_ip: Mapped[str | None] = mapped_column(
        INET,
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    usuario: Mapped[Usuario] = relationship(
        "Usuario",
        back_populates="sesiones",
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        UniqueConstraint(
            "identificador_sesion",
            name="uq_sesion_identificador",
        ),
        UniqueConstraint(
            "refresh_token_hash",
            name="uq_sesion_refresh_token_hash",
        ),
        CheckConstraint(
            "fecha_expiracion > fecha_creacion",
            name="ck_sesion_expiracion",
        ),
        CheckConstraint(
            """
            fecha_revocacion IS NULL
            OR fecha_revocacion >= fecha_creacion
            """,
            name="ck_sesion_revocacion",
        ),
        Index(
            "idx_sesion_usuario",
            "id_usuario",
        ),
        Index(
            "idx_sesion_usuario_vigente",
            "id_usuario",
            "fecha_expiracion",
            postgresql_where=text(
                "fecha_revocacion IS NULL"
            ),
        ),
        Index(
            "idx_sesion_expiracion",
            "fecha_expiracion",
        ),
    )

    @property
    def esta_revocada(self) -> bool:
        return self.fecha_revocacion is not None

    @property
    def esta_expirada(self) -> bool:
        ahora = datetime.now(timezone.utc)
        return self.fecha_expiracion <= ahora

    @property
    def esta_vigente(self) -> bool:
        return not self.esta_revocada and not self.esta_expirada

    def revocar(
        self,
        motivo: str | None = None,
        fecha: datetime | None = None,
    ) -> None:
        self.fecha_revocacion = fecha or datetime.now(timezone.utc)
        self.motivo_revocacion = motivo

    def actualizar_actividad(
        self,
        fecha: datetime | None = None,
    ) -> None:
        self.fecha_ultima_actividad = (
            fecha or datetime.now(timezone.utc)
        )

    def __repr__(self) -> str:
        return (
            "SesionUsuario("
            f"id_sesion={self.id_sesion!r}, "
            f"id_usuario={self.id_usuario!r}, "
            f"identificador_sesion={self.identificador_sesion!r}, "
            f"fecha_expiracion={self.fecha_expiracion!r}, "
            f"fecha_revocacion={self.fecha_revocacion!r}"
            ")"
        )