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

DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FUNCIONES DE CONFIGURACIÓN
# ============================================================

def get_required_env(name: str) -> str:
    """
    Obtiene una variable de entorno obligatoria.

    El backend no debe iniciar si falta un secreto o una
    configuración crítica.
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

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"false", "0", "no", "off"}:
        return False

    raise RuntimeError(
        f"La variable {name!r} debe contener un valor booleano."
    )


def get_positive_float_env(
    name: str,
    default: float,
) -> float:
    """
    Obtiene una variable numérica decimal mayor que cero.
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


# ============================================================
# BASE DE DATOS
# ============================================================

DATABASE_URL = get_required_env("DATABASE_URL")


# ============================================================
# OLLAMA Y RAG
# ============================================================

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://ollama:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b",
)

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    (
        "sentence-transformers/"
        "paraphrase-multilingual-MiniLM-L12-v2"
    ),
)

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
# API EXTERNA DE PAGOS / FACTURACIÓN
# ============================================================
#
# En desarrollo:
#     PAGO_API_BASE_URL=http://mock_pago_api:9000
#
# En producción:
#     PAGO_API_BASE_URL=<URL proporcionada institucionalmente>
#
# Ninguna URL, código de concepto ni credencial se almacena
# directamente en la lógica de negocio.
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

JWT_SECRET_KEY = get_required_env("JWT_SECRET_KEY")

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
        "COOKIE_SAMESITE debe ser 'lax', 'strict' o 'none'."
    )

if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
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
# CORREO ELECTRÓNICO
# ============================================================

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "",
).strip()

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587",
    )
)

SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME",
    "",
).strip()

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD",
    "",
)

SMTP_USE_TLS = get_bool_env(
    "SMTP_USE_TLS",
    default=True,
)

SMTP_USE_SSL = get_bool_env(
    "SMTP_USE_SSL",
    default=False,
)

EMAIL_FROM_ADDRESS = os.getenv(
    "EMAIL_FROM_ADDRESS",
    SMTP_USERNAME,
).strip()

EMAIL_FROM_NAME = os.getenv(
    "EMAIL_FROM_NAME",
    "Sistema de Trámites Académicos UCB",
).strip()

FRONTEND_BASE_URL = os.getenv(
    "FRONTEND_BASE_URL",
    "http://localhost:4200",
).rstrip("/")


if SMTP_USE_TLS and SMTP_USE_SSL:
    raise RuntimeError(
        "SMTP_USE_TLS y SMTP_USE_SSL no pueden estar "
        "activados simultáneamente."
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