from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auditoria import Auditoria
    from app.models.evento_autenticacion import EventoAutenticacion
    from app.models.rol import Rol
    from app.models.sesion_usuario import SesionUsuario
    from app.models.token_recuperacion_contrasena import (
        TokenRecuperacionContrasena,
    )
    from app.models.usuario_correo import UsuarioCorreo
    from app.models.usuario_rol import UsuarioRol


class Usuario(Base):
    """
    Representa la cuenta general de una persona dentro del sistema.

    El correo, los roles y las sesiones se administran en tablas
    independientes para permitir varios correos, varios roles y
    revocación individual de sesiones.
    """

    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    nombres: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    apellidos: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Contendrá un hash Argon2, nunca la contraseña en texto plano.
    # Puede ser NULL para permitir posteriormente autenticación externa.
    contrasena_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pendiente_verificacion",
        server_default=text("'pendiente_verificacion'"),
    )

    fecha_ultimo_acceso: Mapped[datetime | None] = mapped_column(
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

    correos: Mapped[list[UsuarioCorreo]] = relationship(
        "UsuarioCorreo",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    asignaciones_rol: Mapped[list[UsuarioRol]] = relationship(
        "UsuarioRol",
        foreign_keys="UsuarioRol.id_usuario",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    roles: Mapped[list[Rol]] = relationship(
        "Rol",
        secondary="usuario_rol",
        primaryjoin="Usuario.id_usuario == UsuarioRol.id_usuario",
        secondaryjoin="Rol.id_rol == UsuarioRol.id_rol",
        viewonly=True,
    )

    sesiones: Mapped[list[SesionUsuario]] = relationship(
        "SesionUsuario",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    tokens_recuperacion: Mapped[
        list[TokenRecuperacionContrasena]
    ] = relationship(
        "TokenRecuperacionContrasena",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    eventos_autenticacion: Mapped[
        list[EventoAutenticacion]
    ] = relationship(
        "EventoAutenticacion",
        back_populates="usuario",
        passive_deletes=True,
    )

    auditorias_realizadas: Mapped[list[Auditoria]] = relationship(
        "Auditoria",
        foreign_keys="Auditoria.id_usuario_actor",
        back_populates="usuario_actor",
        passive_deletes=True,
    )

    # Roles que este usuario asignó a otras cuentas.
    asignaciones_rol_realizadas: Mapped[list[UsuarioRol]] = relationship(
        "UsuarioRol",
        foreign_keys="UsuarioRol.asignado_por",
        back_populates="usuario_asignador",
        passive_deletes=True,
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        CheckConstraint(
            "LENGTH(TRIM(nombres)) >= 2",
            name="ck_usuario_nombres_no_vacios",
        ),
        CheckConstraint(
            "LENGTH(TRIM(apellidos)) >= 2",
            name="ck_usuario_apellidos_no_vacios",
        ),
        CheckConstraint(
            """
            estado IN (
                'pendiente_verificacion',
                'activo',
                'bloqueado',
                'inactivo'
            )
            """,
            name="ck_usuario_estado",
        ),
        Index(
            "idx_usuario_estado",
            "estado",
        ),
    )

    @property
    def nombre_completo(self) -> str:
        """Devuelve nombres y apellidos sin espacios sobrantes."""
        return f"{self.nombres.strip()} {self.apellidos.strip()}"

    @property
    def esta_activo(self) -> bool:
        """Indica si la cuenta puede utilizar funciones autenticadas."""
        return self.estado == "activo"

    @property
    def correo_principal(self) -> UsuarioCorreo | None:
        """
        Devuelve el correo principal activo.

        Se calcula sobre la relación cargada; no realiza una consulta
        adicional por sí mismo.
        """
        return next(
            (
                correo
                for correo in self.correos
                if correo.es_principal and correo.activo
            ),
            None,
        )

    def tiene_rol(self, nombre_rol: str) -> bool:
        """
        Comprueba si el usuario tiene un rol activo.

        Se revisan las asignaciones de rol para no considerar
        relaciones revocadas o inactivas.
        """
        nombre_normalizado = nombre_rol.strip().lower()

        return any(
            asignacion.activo
            and asignacion.rol.activo
            and asignacion.rol.nombre.lower() == nombre_normalizado
            for asignacion in self.asignaciones_rol
        )

    def __repr__(self) -> str:
        return (
            "Usuario("
            f"id_usuario={self.id_usuario!r}, "
            f"nombres={self.nombres!r}, "
            f"apellidos={self.apellidos!r}, "
            f"estado={self.estado!r}"
            ")"
        )