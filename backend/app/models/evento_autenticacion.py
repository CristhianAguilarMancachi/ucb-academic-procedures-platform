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
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class EventoAutenticacion(Base):
    """
    Registra eventos relacionados con la autenticación.

    Permite conservar información sobre registros, accesos,
    cierres de sesión, recuperaciones y bloqueos de cuenta.
    """

    __tablename__ = "evento_autenticacion"

    id_evento_autenticacion: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_usuario: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            ondelete="SET NULL",
            name="fk_evento_autenticacion_usuario",
        ),
        nullable=True,
    )

    correo_intentado: Mapped[str | None] = mapped_column(
        CITEXT,
        nullable=True,
    )

    tipo_evento: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    exitoso: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    motivo_fallo: Mapped[str | None] = mapped_column(
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

    fecha_evento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    usuario: Mapped[Usuario | None] = relationship(
        "Usuario",
        back_populates="eventos_autenticacion",
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        CheckConstraint(
            """
            tipo_evento IN (
                'registro',
                'verificacion_correo',
                'inicio_sesion',
                'renovacion_sesion',
                'cierre_sesion',
                'solicitud_recuperacion',
                'cambio_contrasena',
                'cambio_correo',
                'bloqueo_cuenta',
                'desbloqueo_cuenta'
            )
            """,
            name="ck_evento_autenticacion_tipo",
        ),
        Index(
            "idx_evento_autenticacion_usuario",
            "id_usuario",
        ),
        Index(
            "idx_evento_autenticacion_correo_fecha",
            "correo_intentado",
            text("fecha_evento DESC"),
        ),
        Index(
            "idx_evento_autenticacion_ip_fecha",
            "direccion_ip",
            text("fecha_evento DESC"),
        ),
        Index(
            "idx_evento_autenticacion_fallido",
            text("fecha_evento DESC"),
            postgresql_where=text("exitoso = FALSE"),
        ),
    )

    @property
    def es_fallido(self) -> bool:
        return not self.exitoso

    def __repr__(self) -> str:
        return (
            "EventoAutenticacion("
            f"id_evento_autenticacion="
            f"{self.id_evento_autenticacion!r}, "
            f"id_usuario={self.id_usuario!r}, "
            f"tipo_evento={self.tipo_evento!r}, "
            f"exitoso={self.exitoso!r}, "
            f"fecha_evento={self.fecha_evento!r}"
            ")"
        )