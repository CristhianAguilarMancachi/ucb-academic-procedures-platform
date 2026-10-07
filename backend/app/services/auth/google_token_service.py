from __future__ import annotations

from dataclasses import dataclass

from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import GOOGLE_CLIENT_ID


# ============================================================
# EXCEPCIONES
# ============================================================

class GoogleTokenServiceError(Exception):
    """
    Error base relacionado con autenticación mediante Google.
    """


class GoogleNoConfiguradoError(GoogleTokenServiceError):
    """
    Google Identity Services todavía no está configurado.
    """


class GoogleTokenInvalidoError(GoogleTokenServiceError):
    """
    El token recibido no pudo ser validado.
    """


class GoogleCorreoNoVerificadoError(GoogleTokenServiceError):
    """
    Google no confirmó el correo asociado a la identidad.
    """


# ============================================================
# RESULTADO SEGURO DE LA VALIDACIÓN
# ============================================================

@dataclass(frozen=True, slots=True)
class IdentidadGoogle:
    """
    Datos de identidad obtenidos únicamente después de validar
    correctamente el ID token emitido por Google.

    El atributo `sub` es el identificador estable de la cuenta
    dentro de Google.
    """

    sub: str
    correo: str
    nombres: str
    apellidos: str
    correo_verificado: bool


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _normalizar_texto(
    valor: object,
) -> str:
    if not isinstance(valor, str):
        return ""

    return " ".join(
        valor.strip().split()
    )


def _extraer_nombres(
    payload: dict,
) -> tuple[str, str]:
    """
    Obtiene nombres y apellidos desde los claims de Google.

    Se utilizan given_name y family_name cuando están disponibles.
    Como alternativa se utiliza el claim name.
    """
    nombres = _normalizar_texto(
        payload.get("given_name")
    )

    apellidos = _normalizar_texto(
        payload.get("family_name")
    )

    if nombres and apellidos:
        return nombres, apellidos

    nombre_completo = _normalizar_texto(
        payload.get("name")
    )

    if not nombre_completo:
        return (
            nombres or "Usuario",
            apellidos or "Google",
        )

    partes = nombre_completo.split()

    if not nombres:
        nombres = partes[0]

    if not apellidos:
        if len(partes) > 1:
            apellidos = " ".join(partes[1:])
        else:
            apellidos = "Google"

    return nombres, apellidos


# ============================================================
# VALIDACIÓN DEL ID TOKEN
# ============================================================

def verificar_token_google(
    credential: str,
) -> IdentidadGoogle:
    """
    Valida un Google ID token contra el Client ID configurado.

    Nunca se confía directamente en los datos enviados por el
    frontend. La identidad se obtiene exclusivamente del token
    validado criptográficamente.
    """
    if not GOOGLE_CLIENT_ID:
        raise GoogleNoConfiguradoError(
            "El acceso con Google todavía no está configurado."
        )

    token = credential.strip()

    if not token:
        raise GoogleTokenInvalidoError(
            "No se recibió una credencial válida de Google."
        )

    try:
        payload = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )

    except (
        ValueError,
        GoogleAuthError,
    ) as exc:
        raise GoogleTokenInvalidoError(
            "La credencial de Google no es válida o ha expirado."
        ) from exc

    issuer = str(
        payload.get(
            "iss",
            "",
        )
    ).strip()

    if issuer not in {
        "accounts.google.com",
        "https://accounts.google.com",
    }:
        raise GoogleTokenInvalidoError(
            "La credencial no fue emitida por Google."
        )

    sub = str(
        payload.get(
            "sub",
            "",
        )
    ).strip()

    correo = str(
        payload.get(
            "email",
            "",
        )
    ).strip().lower()

    correo_verificado = (
        payload.get("email_verified")
        is True
    )

    if not sub:
        raise GoogleTokenInvalidoError(
            "Google no proporcionó un identificador válido."
        )

    if not correo:
        raise GoogleTokenInvalidoError(
            "Google no proporcionó un correo electrónico."
        )

    if not correo_verificado:
        raise GoogleCorreoNoVerificadoError(
            "Google no confirmó el correo electrónico de la cuenta."
        )

    nombres, apellidos = _extraer_nombres(
        payload
    )

    return IdentidadGoogle(
        sub=sub,
        correo=correo,
        nombres=nombres,
        apellidos=apellidos,
        correo_verificado=True,
    )