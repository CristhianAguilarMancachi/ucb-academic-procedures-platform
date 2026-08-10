from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
)


TipoToken = Literal[
    "access",
    "refresh",
    "verificacion_correo",
    "recuperacion_contrasena",
]


class AccessTokenPayload(BaseModel):
    """
    Contenido validado del JWT de acceso.

    Incluye los claims necesarios para verificar identidad,
    sesión, vigencia, emisor y audiencia.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    sub: str
    session_id: UUID

    token_type: Literal["access"] = "access"

    roles: list[str] = Field(
        default_factory=list,
    )

    iat: int
    nbf: int
    exp: int

    jti: str

    iss: str
    aud: str


class RefreshTokenPayload(BaseModel):
    """
    Representación lógica de un refresh token.

    El refresh token real será aleatorio y no necesariamente
    un JWT. Este schema sirve para transportar los datos
    asociados durante el proceso interno.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    id_usuario: int = Field(
        gt=0,
    )

    identificador_sesion: UUID
    fecha_expiracion: datetime


class TokenGenerado(BaseModel):
    """
    Resultado interno de la creación de un token aleatorio.

    El valor original se entrega al usuario y su hash se
    almacena en PostgreSQL.
    """

    valor: str
    hash: str
    fecha_expiracion: datetime


class TokenVerificacionRequest(BaseModel):
    """
    Token recibido desde el enlace de verificación de correo.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    token: SecretStr = Field(
        min_length=32,
        max_length=512,
    )


class TokenRecuperacionRequest(BaseModel):
    """
    Token recibido desde el enlace de recuperación
    de contraseña.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    token: SecretStr = Field(
        min_length=32,
        max_length=512,
    )


class TokenEstadoResponse(BaseModel):
    """
    Resultado de la validación de un token temporal.

    No expone el hash guardado en PostgreSQL.
    """

    valido: bool
    tipo: TipoToken

    fecha_expiracion: datetime | None = None
    utilizado: bool = False
    revocado: bool = False

    mensaje: str


class TokenRotacionResponse(BaseModel):
    """
    Tokens emitidos después de rotar una sesión.

    El refresh token puede omitirse si se envía mediante
    cookie HttpOnly.
    """

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(
        gt=0,
    )

    refresh_token: str | None = None


class TokenRevocarRequest(BaseModel):
    """
    Revoca el refresh token correspondiente a una sesión.

    En Angular normalmente se obtendrá desde una cookie
    HttpOnly. Este campo permite realizar pruebas desde
    Swagger o utilizar otros clientes.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    refresh_token: SecretStr | None = Field(
        default=None,
        min_length=32,
        max_length=512,
    )