from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
)


TipoCorreo = Literal[
    "institucional",
    "personal",
]


class CorreoAgregarRequest(BaseModel):
    """
    Agrega un nuevo correo a una cuenta autenticada.

    El correo quedará sin verificar hasta que el usuario
    complete el proceso de confirmación.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    correo: EmailStr
    tipo: TipoCorreo
    establecer_como_principal: bool = False


class CorreoVerificarRequest(BaseModel):
    """
    Verifica un correo mediante el token enviado.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    token: SecretStr = Field(
        min_length=32,
        max_length=512,
    )


class CorreoReenviarVerificacionRequest(BaseModel):
    """
    Solicita un nuevo enlace o código de verificación.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    correo: EmailStr


class CorreoPrincipalActualizarRequest(BaseModel):
    """
    Establece un correo verificado como principal.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    id_usuario_correo: int = Field(
        gt=0,
    )


class CorreoEliminarRequest(BaseModel):
    """
    Permite desactivar un correo asociado a la cuenta.

    La contraseña actual ayuda a proteger una operación
    sensible de modificación de acceso.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    contrasena_actual: SecretStr = Field(
        min_length=1,
        max_length=128,
    )


class CorreoResponse(BaseModel):
    """
    Correo asociado a una cuenta.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_usuario_correo: int
    correo: EmailStr
    tipo: TipoCorreo
    es_principal: bool
    verificado: bool
    activo: bool
    fecha_verificacion: datetime | None
    fecha_creacion: datetime


class CorreoResumenResponse(BaseModel):
    """
    Vista reducida para login y administración.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_usuario_correo: int
    correo: EmailStr
    tipo: TipoCorreo
    es_principal: bool
    verificado: bool