from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class RolResponse(BaseModel):
    """
    Rol asignable dentro del sistema.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_rol: int
    nombre: str
    descripcion: str | None
    activo: bool


class RolDetalleResponse(RolResponse):
    """
    Vista administrativa ampliada de un rol.
    """

    fecha_creacion: datetime
    fecha_actualizacion: datetime


class RolAsignarRequest(BaseModel):
    """
    Asigna un rol a una cuenta.

    Solo podrá utilizarse desde endpoints administrativos.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    id_rol: int = Field(
        gt=0,
    )


class RolRevocarRequest(BaseModel):
    """
    Revoca un rol de una cuenta.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    motivo: str | None = Field(
        default=None,
        min_length=3,
        max_length=500,
    )


class UsuarioRolResponse(BaseModel):
    """
    Representa una asignación de rol concreta.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_usuario_rol: int
    id_usuario: int
    id_rol: int
    activo: bool
    asignado_por: int | None
    fecha_asignacion: datetime
    fecha_revocacion: datetime | None
    rol: RolResponse


class ListaRolesResponse(BaseModel):
    """
    Catálogo de roles disponibles.
    """

    items: list[RolResponse]
    total: int