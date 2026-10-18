from __future__ import annotations

import hashlib
import hmac
import time
from uuid import UUID

from fastapi import Request, Response

from app.core.config import COOKIE_SECURE, JWT_SECRET_KEY

COOKIE_NAME = "ucb_rag_visitante"
COOKIE_PATH = "/api/rag"
MAX_SECONDS = 12 * 60 * 60


def _signature(value: str) -> str:
    return hmac.new(
        JWT_SECRET_KEY.encode("utf-8"),
        value.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def read_visitor_id(request: Request) -> UUID | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None

    try:
        session_hex, expiry, supplied_signature = token.split(".")
        session_id = UUID(hex=session_hex)
        expires_at = int(expiry)
        unsigned = f"{session_hex}.{expiry}"

        if expires_at <= int(time.time()):
            return None

        if expires_at > int(time.time()) + MAX_SECONDS:
            return None

        if not hmac.compare_digest(
            _signature(unsigned),
            supplied_signature,
        ):
            return None

        return session_id
    except (ValueError, TypeError, AttributeError):
        return None


def set_visitor_cookie(
    response: Response,
    session_id: UUID,
) -> None:
    expiry = int(time.time()) + MAX_SECONDS
    unsigned = f"{session_id.hex}.{expiry}"
    token = f"{unsigned}.{_signature(unsigned)}"

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path=COOKIE_PATH,
    )


def delete_visitor_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
