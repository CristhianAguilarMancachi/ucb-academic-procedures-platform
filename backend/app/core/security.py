from __future__ import annotations

import hashlib
import secrets
import uuid

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID


import jwt

from jwt import (
    ExpiredSignatureError,
    InvalidTokenError,
)

from pwdlib import PasswordHash


from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    EMAIL_VERIFICATION_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    JWT_SECRET_KEY,
    PASSWORD_RESET_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

from app.schemas.tokens import (
    AccessTokenPayload,
    TokenGenerado,
)


password_hash = PasswordHash.recommended()


class TokenSecurityError(Exception):
    """
    Error base relacionado con validación de tokens.
    """


class TokenExpiradoError(TokenSecurityError):
    """
    El token tiene una fecha de expiración vencida.
    """


class TokenInvalidoError(TokenSecurityError):
    """
    El token no tiene firma, estructura o claims válidos.
    """


# ============================================================
# FECHA Y HORA
# ============================================================

def utc_now() -> datetime:
    """
    Devuelve la fecha actual con zona horaria UTC.
    """
    return datetime.now(timezone.utc)


# ============================================================
# CONTRASEÑAS
# ============================================================

def generar_hash_contrasena(
    contrasena: str,
) -> str:
    """
    Genera un hash Argon2 para una contraseña.

    Nunca debe guardarse la contraseña original.
    """
    if not contrasena:
        raise ValueError(
            "La contraseña no puede estar vacía."
        )

    return password_hash.hash(contrasena)


def verificar_contrasena(
    contrasena: str,
    contrasena_hash: str | None,
) -> bool:
    """
    Comprueba una contraseña contra un hash Argon2.

    Devuelve False cuando la cuenta no tiene contraseña local
    o cuando el hash recibido no es válido.
    """
    if not contrasena or not contrasena_hash:
        return False

    try:
        return password_hash.verify(
            contrasena,
            contrasena_hash,
        )
    except Exception:
        return False


def verificar_y_actualizar_hash(
    contrasena: str,
    contrasena_hash: str,
) -> tuple[bool, str | None]:
    """
    Verifica una contraseña y devuelve un hash actualizado
    cuando los parámetros de seguridad hayan cambiado.
    """
    try:
        valido, nuevo_hash = password_hash.verify_and_update(
            contrasena,
            contrasena_hash,
        )

        return valido, nuevo_hash

    except Exception:
        return False, None


# ============================================================
# HASH DE TOKENS ALEATORIOS
# ============================================================

def generar_token_aleatorio(
    cantidad_bytes: int = 48,
) -> str:
    """
    Genera un token criptográficamente seguro.

    Se utiliza para refresh tokens, verificación de correo
    y recuperación de contraseña.
    """
    if cantidad_bytes < 32:
        raise ValueError(
            "El token debe generarse con al menos 32 bytes."
        )

    return secrets.token_urlsafe(cantidad_bytes)


def generar_hash_token(
    token: str,
) -> str:
    """
    Genera el SHA-256 hexadecimal de un token.

    PostgreSQL almacena este hash, no el token original.
    """
    if not token:
        raise ValueError(
            "El token no puede estar vacío."
        )

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def comparar_token_con_hash(
    token: str,
    token_hash: str,
) -> bool:
    """
    Compara de manera resistente a análisis de tiempo
    un token con el hash almacenado.
    """
    if not token or not token_hash:
        return False

    calculado = generar_hash_token(token)

    return secrets.compare_digest(
        calculado,
        token_hash,
    )


# ============================================================
# ACCESS TOKEN JWT
# ============================================================

def crear_access_token(
    *,
    id_usuario: int,
    identificador_sesion: UUID,
    roles: list[str],
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """
    Crea un JWT de acceso firmado.

    El token contiene únicamente información necesaria para
    identificar al usuario, la sesión y sus roles.
    """
    ahora = utc_now()

    expiracion = ahora + (
        expires_delta
        or timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload: dict[str, Any] = {
        "sub": str(id_usuario),
        "session_id": str(identificador_sesion),
        "token_type": "access",
        "roles": roles,
        "iat": ahora,
        "nbf": ahora,
        "exp": expiracion,
        "jti": str(uuid.uuid4()),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return token, expiracion


def decodificar_access_token(
    token: str,
) -> AccessTokenPayload:
    """
    Valida firma, algoritmo, expiración, emisor, audiencia
    y claims obligatorios de un JWT de acceso.
    """
    if not token:
        raise TokenInvalidoError(
            "No se recibió el token de acceso."
        )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={
                "require": [
                    "sub",
                    "session_id",
                    "token_type",
                    "roles",
                    "iat",
                    "exp",
                    "jti",
                    "iss",
                    "aud",
                ]
            },
        )

        if payload.get("token_type") != "access":
            raise TokenInvalidoError(
                "El token no es un access token."
            )

        return AccessTokenPayload.model_validate(
            payload
        )

    except ExpiredSignatureError as exc:
        raise TokenExpiradoError(
            "El token de acceso ha expirado."
        ) from exc

    except TokenSecurityError:
        raise

    except (
        InvalidTokenError,
        ValueError,
        TypeError,
    ) as exc:
        raise TokenInvalidoError(
            "El token de acceso no es válido."
        ) from exc


# ============================================================
# REFRESH TOKEN
# ============================================================

def crear_refresh_token() -> TokenGenerado:
    """
    Crea un refresh token aleatorio y su hash.

    El valor original se entrega mediante cookie HttpOnly.
    Solo el hash se almacena en sesion_usuario.
    """
    valor = generar_token_aleatorio()

    fecha_expiracion = utc_now() + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    return TokenGenerado(
        valor=valor,
        hash=generar_hash_token(valor),
        fecha_expiracion=fecha_expiracion,
    )


# ============================================================
# VERIFICACIÓN DE CORREO
# ============================================================

def crear_token_verificacion_correo() -> TokenGenerado:
    """
    Crea un token temporal para verificar un correo.
    """
    valor = generar_token_aleatorio()

    fecha_expiracion = utc_now() + timedelta(
        minutes=EMAIL_VERIFICATION_EXPIRE_MINUTES
    )

    return TokenGenerado(
        valor=valor,
        hash=generar_hash_token(valor),
        fecha_expiracion=fecha_expiracion,
    )


# ============================================================
# RECUPERACIÓN DE CONTRASEÑA
# ============================================================

def crear_token_recuperacion_contrasena() -> TokenGenerado:
    """
    Crea un token temporal para restablecer una contraseña.
    """
    valor = generar_token_aleatorio()

    fecha_expiracion = utc_now() + timedelta(
        minutes=PASSWORD_RESET_EXPIRE_MINUTES
    )

    return TokenGenerado(
        valor=valor,
        hash=generar_hash_token(valor),
        fecha_expiracion=fecha_expiracion,
    )