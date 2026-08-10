from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class RegistroRequest(BaseModel):
    """
    Datos requeridos para crear una cuenta.

    El primer correo se registrará como principal y quedará
    pendiente de verificación.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    nombres: str = Field(
        min_length=2,
        max_length=100,
        examples=["Cristhian Rodrigo"],
    )

    apellidos: str = Field(
        min_length=2,
        max_length=100,
        examples=["Aguilar Mancachi"],
    )

    correo: EmailStr = Field(
        examples=["usuario@correo.com"],
    )

    contrasena: SecretStr = Field(
        min_length=8,
        max_length=128,
    )

    confirmar_contrasena: SecretStr = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator("nombres", "apellidos")
    @classmethod
    def validar_texto_nombre(cls, value: str) -> str:
        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El campo debe contener al menos una letra."
            )

        return value

    @model_validator(mode="after")
    def validar_contrasenas(self) -> "RegistroRequest":
        if (
            self.contrasena.get_secret_value()
            != self.confirmar_contrasena.get_secret_value()
        ):
            raise ValueError(
                "Las contraseñas no coinciden."
            )

        return self


class LoginRequest(BaseModel):
    """
    Credenciales para iniciar sesión.

    El usuario podrá ingresar con cualquiera de sus correos
    activos y verificados.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    correo: EmailStr
    contrasena: SecretStr = Field(
        min_length=1,
        max_length=128,
    )


class RefreshTokenRequest(BaseModel):
    """
    Se utilizará únicamente si el refresh token se recibe
    en el cuerpo de la petición.

    Para el frontend Angular usaremos preferentemente una
    cookie HttpOnly, por lo que este schema también será útil
    para pruebas desde Swagger o clientes externos.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    refresh_token: SecretStr | None = Field(
        default=None,
        min_length=32,
        max_length=512,
    )

class LogoutRequest(BaseModel):
    """
    Permite cerrar una sesión específica.

    Si el refresh token se obtiene desde una cookie HttpOnly,
    el endpoint podrá no requerir cuerpo.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    cerrar_todas_las_sesiones: bool = False


class CambioContrasenaRequest(BaseModel):
    """
    Cambio de contraseña realizado por un usuario autenticado.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    contrasena_actual: SecretStr = Field(
        min_length=1,
        max_length=128,
    )

    nueva_contrasena: SecretStr = Field(
        min_length=8,
        max_length=128,
    )

    confirmar_nueva_contrasena: SecretStr = Field(
        min_length=8,
        max_length=128,
    )

    @model_validator(mode="after")
    def validar_cambio_contrasena(
        self,
    ) -> "CambioContrasenaRequest":
        actual = self.contrasena_actual.get_secret_value()
        nueva = self.nueva_contrasena.get_secret_value()
        confirmacion = (
            self.confirmar_nueva_contrasena.get_secret_value()
        )

        if nueva != confirmacion:
            raise ValueError(
                "Las nuevas contraseñas no coinciden."
            )

        if actual == nueva:
            raise ValueError(
                "La nueva contraseña debe ser diferente "
                "de la contraseña actual."
            )

        return self


class SolicitudRecuperacionRequest(BaseModel):
    """
    Solicitud de recuperación de contraseña.

    El endpoint siempre debe responder de forma genérica,
    exista o no el correo.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    correo: EmailStr


class RestablecerContrasenaRequest(BaseModel):
    """
    Establece una nueva contraseña utilizando un token
    temporal de recuperación.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    token: SecretStr = Field(
        min_length=32,
        max_length=512,
    )

    nueva_contrasena: SecretStr = Field(
        min_length=8,
        max_length=128,
    )

    confirmar_nueva_contrasena: SecretStr = Field(
        min_length=8,
        max_length=128,
    )

    @model_validator(mode="after")
    def validar_nuevas_contrasenas(
        self,
    ) -> "RestablecerContrasenaRequest":
        if (
            self.nueva_contrasena.get_secret_value()
            != self.confirmar_nueva_contrasena.get_secret_value()
        ):
            raise ValueError(
                "Las contraseñas no coinciden."
            )

        return self


class MensajeResponse(BaseModel):
    """
    Respuesta genérica para operaciones que solo necesitan
    confirmar el resultado.
    """

    mensaje: str


class RegistroResponse(BaseModel):
    """
    Respuesta después de crear una cuenta.
    """

    id_usuario: int
    correo: EmailStr
    estado: str
    requiere_verificacion: bool = True
    mensaje: str


class TokenResponse(BaseModel):
    """
    Tokens emitidos después del login o de una renovación.

    El refresh token puede omitirse en la respuesta cuando
    se envía exclusivamente mediante cookie HttpOnly.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None


class LoginResponse(BaseModel):
    """
    Respuesta completa del inicio de sesión.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None
    usuario: "UsuarioAutenticadoResponse"


from app.schemas.usuario import UsuarioAutenticadoResponse

LoginResponse.model_rebuild()