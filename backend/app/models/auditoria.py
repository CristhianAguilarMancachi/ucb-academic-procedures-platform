from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class Auditoria(Base):
    """
    Registra acciones sensibles realizadas dentro del sistema.

    Puede utilizarse para cambios de roles, estados de cuenta,
    modificaciones administrativas y operaciones sobre trámites.
    """

    __tablename__ = "auditoria"

    id_auditoria: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_usuario_actor: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="SET NULL",
            name="fk_auditoria_usuario_actor",
        ),
        nullable=True,
    )

    accion: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    modulo: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    entidad: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    id_entidad: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    exitoso: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    detalle: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
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

    fecha_evento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    usuario_actor: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[id_usuario_actor],
        back_populates="auditorias_realizadas",
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        CheckConstraint(
            "LENGTH(TRIM(accion)) >= 3",
            name="ck_auditoria_accion_no_vacia",
        ),
        CheckConstraint(
            "LENGTH(TRIM(modulo)) >= 3",
            name="ck_auditoria_modulo_no_vacio",
        ),
        Index(
            "idx_auditoria_usuario",
            "id_usuario_actor",
        ),
        Index(
            "idx_auditoria_fecha",
            text("fecha_evento DESC"),
        ),
        Index(
            "idx_auditoria_modulo",
            "modulo",
            text("fecha_evento DESC"),
        ),
        Index(
            "idx_auditoria_entidad",
            "entidad",
            "id_entidad",
        ),
    )

    def __repr__(self) -> str:
        return (
            "Auditoria("
            f"id_auditoria={self.id_auditoria!r}, "
            f"id_usuario_actor={self.id_usuario_actor!r}, "
            f"accion={self.accion!r}, "
            f"modulo={self.modulo!r}, "
            f"exitoso={self.exitoso!r}, "
            f"fecha_evento={self.fecha_evento!r}"
            ")"
        )