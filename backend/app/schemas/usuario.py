from __future__ import annotations

from datetime import datetime
from typing import Literal

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


class UsuarioBase(BaseModel):
    """
    Datos generales y reutilizables de una cuenta.
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

    @field_validator("nombres", "apellidos")
    @classmethod
    def normalizar_nombre(cls, value: str) -> str:
        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El campo debe contener al menos una letra."
            )

        return value


class UsuarioActualizarRequest(BaseModel):
    """
    Permite modificar los datos personales básicos.

    No incluye correo, contraseña, estado ni roles porque
    esas operaciones tienen flujos independientes.
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

    @field_validator("nombres", "apellidos")
    @classmethod
    def normalizar_nombre_opcional(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El campo debe contener al menos una letra."
            )

        return value


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


class UsuarioResumenResponse(BaseModel):
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
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"


class UsuarioResponse(BaseModel):
    """
    Información general de una cuenta.
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
    fecha_actualizacion: datetime


class UsuarioAutenticadoResponse(UsuarioResponse):
    """
    Información del usuario autenticado.

    Incluye correos y roles, pero nunca contrasena_hash.
    """

    correos: list[CorreoResponse] = Field(
        default_factory=list,
    )

    roles: list[RolResponse] = Field(
        default_factory=list,
    )


class UsuarioAdministradorDetalleResponse(
    UsuarioAutenticadoResponse
):
    """
    Información ampliada visible para administradores.
    """

    cantidad_sesiones_activas: int = 0


class ListaUsuariosResponse(BaseModel):
    """
    Respuesta paginada para administración de usuarios.
    """

    items: list[UsuarioResumenResponse]
    total: int
    pagina: int = Field(ge=1)
    por_pagina: int = Field(ge=1, le=100)