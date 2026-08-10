from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,

)


class SesionResponse(BaseModel):
    """
    Representa una sesión iniciada por el usuario.

    No expone el refresh token ni su hash.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_sesion: int
    identificador_sesion: UUID

    fecha_creacion: datetime
    fecha_ultima_actividad: datetime
    fecha_expiracion: datetime
    fecha_revocacion: datetime | None

    motivo_revocacion: str | None
    direccion_ip: IPvAnyAddress | None
    user_agent: str | None

    esta_vigente: bool


class SesionResumenResponse(BaseModel):
    """
    Vista reducida de una sesión para mostrarla al usuario.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_sesion: int
    identificador_sesion: UUID

    fecha_creacion: datetime
    fecha_ultima_actividad: datetime
    fecha_expiracion: datetime
    fecha_revocacion: datetime | None

    direccion_ip: IPvAnyAddress | None
    user_agent: str | None


class SesionActualResponse(SesionResumenResponse):
    """
    Representa la sesión desde la cual se está realizando
    actualmente la solicitud.
    """

    es_sesion_actual: bool = True


class ListaSesionesResponse(BaseModel):
    """
    Lista de sesiones pertenecientes al usuario autenticado.
    """

    items: list[SesionResumenResponse]
    total: int


class SesionRevocarRequest(BaseModel):
    """
    Permite revocar una sesión específica.

    El motivo es opcional porque el propio usuario puede
    cerrar una sesión sin necesidad de explicarlo.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    motivo: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )


class SesionRevocarResponse(BaseModel):
    """
    Confirma que una sesión fue revocada.
    """

    id_sesion: int
    identificador_sesion: UUID
    fecha_revocacion: datetime
    mensaje: str


class CerrarTodasSesionesRequest(BaseModel):
    """
    Permite cerrar todas las sesiones de la cuenta.

    Puede conservarse la sesión actual para operaciones
    como cambiar la contraseña sin expulsar inmediatamente
    al usuario del dispositivo en uso.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    conservar_sesion_actual: bool = False


class CerrarTodasSesionesResponse(BaseModel):
    """
    Resultado del cierre masivo de sesiones.
    """

    sesiones_revocadas: int
    sesion_actual_conservada: bool
    mensaje: str