from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


# ============================================================
# DIRECTORIOS
# ============================================================

DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"

DOCUMENTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# FUNCIONES DE CONFIGURACIÓN
# ============================================================

def get_required_env(
    name: str,
) -> str:
    """
    Obtiene una variable de entorno obligatoria.
    """

    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"La variable de entorno obligatoria "
            f"{name!r} no está configurada."
        )

    return value.strip()


def get_bool_env(
    name: str,
    default: bool = False,
) -> bool:
    """
    Convierte una variable de entorno a booleano.
    """

    value = os.getenv(name)

    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized in {
        "true",
        "1",
        "yes",
        "on",
    }:
        return True

    if normalized in {
        "false",
        "0",
        "no",
        "off",
    }:
        return False

    raise RuntimeError(
        f"La variable {name!r} debe contener "
        "un valor booleano."
    )


def get_positive_float_env(
    name: str,
    default: float,
) -> float:
    """
    Obtiene una variable decimal mayor que cero.
    """

    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        result = float(
            value.strip()
        )
    except ValueError as exc:
        raise RuntimeError(
            f"La variable {name!r} debe contener "
            "un valor numérico."
        ) from exc

    if result <= 0:
        raise RuntimeError(
            f"La variable {name!r} debe ser mayor que cero."
        )

    return result


def get_non_negative_int_env(
    name: str,
    default: int,
) -> int:
    """
    Obtiene una variable entera mayor o igual a cero.
    """

    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        result = int(
            value.strip()
        )
    except ValueError as exc:
        raise RuntimeError(
            f"La variable {name!r} debe contener "
            "un número entero."
        ) from exc

    if result < 0:
        raise RuntimeError(
            f"La variable {name!r} no puede ser negativa."
        )

    return result


# ============================================================
# BASE DE DATOS
# ============================================================

DATABASE_URL = get_required_env(
    "DATABASE_URL"
)


# ============================================================
# GROQ - GENERACIÓN DEL RAG
# ============================================================

GROQ_API_KEY = get_required_env(
    "GROQ_API_KEY"
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
).strip()

GROQ_TIMEOUT_SECONDS = get_positive_float_env(
    "GROQ_TIMEOUT_SECONDS",
    default=30.0,
)

GROQ_MAX_RETRIES = get_non_negative_int_env(
    "GROQ_MAX_RETRIES",
    default=2,
)

if not GROQ_MODEL:
    raise RuntimeError(
        "GROQ_MODEL no puede estar vacío."
    )


# ============================================================
# JINA AI - EMBEDDINGS DEL RAG
# ============================================================

JINA_API_KEY = get_required_env(
    "JINA_API_KEY"
)

JINA_API_BASE_URL = os.getenv(
    "JINA_API_BASE_URL",
    "https://api.jina.ai/v1",
).rstrip("/")

JINA_EMBEDDING_MODEL = os.getenv(
    "JINA_EMBEDDING_MODEL",
    "jina-embeddings-v5-text-small",
).strip()

JINA_EMBEDDING_DIMENSION = int(
    os.getenv(
        "JINA_EMBEDDING_DIMENSION",
        "512",
    )
)

JINA_TIMEOUT_SECONDS = get_positive_float_env(
    "JINA_TIMEOUT_SECONDS",
    default=30.0,
)

JINA_MAX_RETRIES = get_non_negative_int_env(
    "JINA_MAX_RETRIES",
    default=2,
)

if not JINA_API_BASE_URL:
    raise RuntimeError(
        "JINA_API_BASE_URL no puede estar vacío."
    )

if not JINA_EMBEDDING_MODEL:
    raise RuntimeError(
        "JINA_EMBEDDING_MODEL no puede estar vacío."
    )

if JINA_EMBEDDING_DIMENSION not in {
    32,
    64,
    128,
    256,
    512,
    1024,
}:
    raise RuntimeError(
        "JINA_EMBEDDING_DIMENSION debe ser "
        "32, 64, 128, 256, 512 o 1024."
    )


# ============================================================
# CONFIGURACIÓN DE RECUPERACIÓN
# ============================================================

CHUNK_SIZE = int(
    os.getenv(
        "CHUNK_SIZE",
        "800",
    )
)

CHUNK_OVERLAP = int(
    os.getenv(
        "CHUNK_OVERLAP",
        "150",
    )
)

TOP_K = int(
    os.getenv(
        "TOP_K",
        "4",
    )
)


# ============================================================
# GOOGLE IDENTITY SERVICES
# ============================================================

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "",
).strip()


# ============================================================
# API EXTERNA DE PAGOS / FACTURACIÓN
# ============================================================

PAGO_API_BASE_URL = get_required_env(
    "PAGO_API_BASE_URL"
).rstrip("/")

PAGO_API_VALIDAR_PATH = os.getenv(
    "PAGO_API_VALIDAR_PATH",
    "/api/v1/facturas/validar",
).strip()

if not PAGO_API_VALIDAR_PATH:
    raise RuntimeError(
        "PAGO_API_VALIDAR_PATH no puede estar vacío."
    )

if not PAGO_API_VALIDAR_PATH.startswith("/"):
    PAGO_API_VALIDAR_PATH = (
        "/" + PAGO_API_VALIDAR_PATH
    )

PAGO_API_TIMEOUT = get_positive_float_env(
    "PAGO_API_TIMEOUT",
    default=10.0,
)

PAGO_API_TOKEN = os.getenv(
    "PAGO_API_TOKEN",
    "",
).strip()


# ============================================================
# JWT Y TOKENS
# ============================================================

JWT_SECRET_KEY = get_required_env(
    "JWT_SECRET_KEY"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)

JWT_ISSUER = os.getenv(
    "JWT_ISSUER",
    "ucb-academic-procedures-platform",
)

JWT_AUDIENCE = os.getenv(
    "JWT_AUDIENCE",
    "ucb-academic-procedures-client",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "15",
    )
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv(
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "7",
    )
)

EMAIL_VERIFICATION_EXPIRE_MINUTES = int(
    os.getenv(
        "EMAIL_VERIFICATION_EXPIRE_MINUTES",
        "1440",
    )
)

PASSWORD_RESET_EXPIRE_MINUTES = int(
    os.getenv(
        "PASSWORD_RESET_EXPIRE_MINUTES",
        "30",
    )
)


# ============================================================
# COOKIES DE AUTENTICACIÓN
# ============================================================

REFRESH_TOKEN_COOKIE_NAME = os.getenv(
    "REFRESH_TOKEN_COOKIE_NAME",
    "ucb_refresh_token",
)

COOKIE_SECURE = get_bool_env(
    "COOKIE_SECURE",
    default=False,
)

COOKIE_HTTPONLY = True

COOKIE_SAMESITE = os.getenv(
    "COOKIE_SAMESITE",
    "lax",
).lower()

COOKIE_PATH = os.getenv(
    "COOKIE_PATH",
    "/",
)

COOKIE_DOMAIN = os.getenv(
    "COOKIE_DOMAIN",
) or None

if COOKIE_SAMESITE not in {
    "lax",
    "strict",
    "none",
}:
    raise RuntimeError(
        "COOKIE_SAMESITE debe ser "
        "'lax', 'strict' o 'none'."
    )

if (
    COOKIE_SAMESITE == "none"
    and not COOKIE_SECURE
):
    raise RuntimeError(
        "COOKIE_SECURE debe ser true cuando "
        "COOKIE_SAMESITE es 'none'."
    )


# ============================================================
# POLÍTICAS DE AUTENTICACIÓN
# ============================================================

PASSWORD_MIN_LENGTH = int(
    os.getenv(
        "PASSWORD_MIN_LENGTH",
        "8",
    )
)

MAX_LOGIN_ATTEMPTS = int(
    os.getenv(
        "MAX_LOGIN_ATTEMPTS",
        "5",
    )
)

LOGIN_ATTEMPT_WINDOW_MINUTES = int(
    os.getenv(
        "LOGIN_ATTEMPT_WINDOW_MINUTES",
        "15",
    )
)


# ============================================================
# CORREO ELECTRÓNICO / BREVO
# ============================================================

BREVO_API_KEY = os.getenv(
    "BREVO_API_KEY",
    "",
).strip()

BREVO_API_BASE_URL = os.getenv(
    "BREVO_API_BASE_URL",
    "https://api.brevo.com/v3",
).rstrip("/")

BREVO_API_TIMEOUT = get_positive_float_env(
    "BREVO_API_TIMEOUT",
    default=20.0,
)

EMAIL_FROM_ADDRESS = os.getenv(
    "EMAIL_FROM_ADDRESS",
    os.getenv(
        "EMAIL_FROM",
        "",
    ),
).strip()

EMAIL_FROM_NAME = os.getenv(
    "EMAIL_FROM_NAME",
    "Sistema de Gestión de Trámites Académicos",
).strip()

FRONTEND_BASE_URL = os.getenv(
    "FRONTEND_BASE_URL",
    "http://localhost:4200",
).rstrip("/")

if not EMAIL_FROM_ADDRESS:
    raise RuntimeError(
        "Debe configurarse EMAIL_FROM "
        "o EMAIL_FROM_ADDRESS."
    )


# ============================================================
# CORS
# ============================================================

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:4200,http://localhost:8080",
    ).split(",")
    if origin.strip()
]