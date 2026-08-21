from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class UnidadBase(BaseModel):
    """
    Datos generales reutilizables de una unidad administrativa.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    nombre: str = Field(
        min_length=3,
        max_length=120,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, value: str) -> str:
        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El nombre debe contener al menos una letra."
            )

        return value


class UnidadCrearRequest(UnidadBase):
    """
    Datos requeridos para registrar una unidad administrativa.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    activo: bool = True


class UnidadActualizarRequest(BaseModel):
    """
    Permite modificar una unidad administrativa existente.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    nombre: str | None = Field(
        default=None,
        min_length=3,
        max_length=120,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=1000,
    )

    activo: bool | None = None

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El nombre debe contener al menos una letra."
            )

        return value


class UnidadResponse(BaseModel):
    """
    Información general de una unidad administrativa.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_unidad: int
    nombre: str
    descripcion: str | None
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class UsuarioUnidadAsignarRequest(BaseModel):
    """
    Asocia un usuario existente con una unidad administrativa.

    El usuario que realiza la asignación se obtiene de la sesión
    autenticada y no se recibe desde el cliente.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    id_usuario: int = Field(
        gt=0,
    )


class UsuarioUnidadResponse(BaseModel):
    """
    Representa una asociación entre usuario y unidad administrativa.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_usuario_unidad: int
    id_usuario: int
    id_unidad: int
    activo: bool
    asignado_por: int | None
    fecha_asignacion: datetime
    fecha_revocacion: datetime | None


class UnidadDetalleResponse(UnidadResponse):
    """
    Información ampliada de una unidad y sus asociaciones vigentes
    o históricas con usuarios.
    """

    usuarios_asignados: list[UsuarioUnidadResponse] = Field(
        default_factory=list,
    )


class ListaUnidadesResponse(BaseModel):
    """
    Respuesta paginada para el catálogo administrativo de unidades.
    """

    items: list[UnidadResponse]
    total: int = Field(ge=0)
    pagina: int = Field(ge=1)
    por_pagina: int = Field(ge=1, le=100)