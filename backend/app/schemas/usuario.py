from __future__ import annotations
from app.schemas.gestion_seguimiento.perfil_academico import PerfilAcademicoResponse
from app.schemas.gestion_seguimiento.unidad import UnidadResponse

from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.correo import CorreoResponse
from app.schemas.rol import RolResponse


EstadoUsuario = Literal[
    "pendiente_verificacion",
    "activo",
    "bloqueado",
    "inactivo",
]


# ============================================================
# DATOS GENERALES
# ============================================================


class UsuarioBase(BaseModel):
    """
    Datos personales generales y reutilizables de una cuenta.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    nombres: str = Field(
        min_length=2,
        max_length=100,
    )

    apellidos: str = Field(
        min_length=2,
        max_length=100,
    )

    telefono: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
    )

    @field_validator(
        "nombres",
        "apellidos",
    )
    @classmethod
    def normalizar_nombre(
        cls,
        value: str,
    ) -> str:
        value = " ".join(
            value.split()
        )

        if not any(
            character.isalpha()
            for character in value
        ):
            raise ValueError(
                "El campo debe contener al menos una letra."
            )

        return value

    @field_validator(
        "telefono",
        mode="before",
    )
    @classmethod
    def normalizar_telefono(
        cls,
        value: Any,
    ) -> Any:
        """
        Normaliza el teléfono.

        Se permiten formatos como:

            +591 71234567
            71234567
            +591-71234567

        Un valor vacío se interpreta como ausencia de teléfono.
        """
        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):
            return value

        value = " ".join(
            value.split()
        )

        if not value:
            return None

        return value


# ============================================================
# ACTUALIZACIÓN DEL PERFIL
# ============================================================


class UsuarioActualizarRequest(BaseModel):
    """
    Permite modificar los datos personales básicos.

    Se puede actualizar:

        - nombres;
        - apellidos;
        - teléfono.

    El correo, contraseña, estado y roles utilizan flujos
    independientes.

    El CI tampoco pertenece a este contrato porque actualmente
    se conserva en perfil_academico.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    nombres: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    apellidos: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    telefono: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
    )

    @field_validator(
        "nombres",
        "apellidos",
    )
    @classmethod
    def normalizar_nombre_opcional(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = " ".join(
            value.split()
        )

        if not any(
            character.isalpha()
            for character in value
        ):
            raise ValueError(
                "El campo debe contener al menos una letra."
            )

        return value

    @field_validator(
        "telefono",
        mode="before",
    )
    @classmethod
    def normalizar_telefono_opcional(
        cls,
        value: Any,
    ) -> Any:
        """
        Permite enviar null o una cadena vacía cuando el usuario
        desea dejar el teléfono sin registrar.
        """
        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):
            return value

        value = " ".join(
            value.split()
        )

        if not value:
            return None

        return value


# ============================================================
# ESTADO
# ============================================================


class UsuarioEstadoActualizarRequest(BaseModel):
    """
    Cambio de estado realizado por un administrador.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    estado: EstadoUsuario

    motivo: str | None = Field(
        default=None,
        min_length=3,
        max_length=500,
    )


# ============================================================
# RESPUESTAS
# ============================================================


class UsuarioResumenResponse(BaseModel):
    correo_principal: str | None = None
    roles: list[RolResponse] = Field(default_factory=list)

    """
    Datos básicos utilizados en listas administrativas.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_usuario: int
    nombres: str
    apellidos: str
    estado: EstadoUsuario
    fecha_ultimo_acceso: datetime | None
    fecha_creacion: datetime

    @property
    def nombre_completo(
        self,
    ) -> str:
        return (
            f"{self.nombres} "
            f"{self.apellidos}"
        )


class UsuarioResponse(BaseModel):
    """
    Información general de una cuenta.

    telefono puede ser null para cuentas antiguas o usuarios
    que todavía no registraron un número.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_usuario: int
    nombres: str
    apellidos: str
    telefono: str | None = None
    estado: EstadoUsuario
    fecha_ultimo_acceso: datetime | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class UsuarioAutenticadoResponse(
    UsuarioResponse
):
    """
    Información del usuario autenticado.

    Incluye los registros de correo y los roles activos,
    pero nunca contrasena_hash.

    tiene_contrasena únicamente informa si la cuenta dispone
    de credenciales locales. No expone el hash ni ningún
    dato sensible asociado a la contraseña.

    La base de datos limita al usuario a un solo correo activo.
    """

    tiene_contrasena: bool

    correos: list[CorreoResponse] = Field(
        default_factory=list,
    )

    roles: list[RolResponse] = Field(
        default_factory=list,
    )


class ActividadUsuarioResponse(BaseModel):
    fecha: datetime
    origen: str
    accion: str
    exitoso: bool


class UsuarioAdministradorDetalleResponse(
    UsuarioAutenticadoResponse
):
    """
    Información ampliada visible para administradores.
    """

    cantidad_sesiones_activas: int = 0
    perfil_academico: PerfilAcademicoResponse | None = None
    unidades: list[UnidadResponse] = Field(default_factory=list)
    actividad_reciente: list[ActividadUsuarioResponse] = Field(default_factory=list)


class ListaUsuariosResponse(BaseModel):
    """
    Respuesta paginada para administración de usuarios.
    """

    items: list[UsuarioResumenResponse]

    total: int

    pagina: int = Field(
        ge=1,
    )

    por_pagina: int = Field(
        ge=1,
        le=100,
    )