from __future__ import annotations

import requests

from app.core.config import (
    BREVO_API_BASE_URL,
    BREVO_API_KEY,
    BREVO_API_TIMEOUT,
    EMAIL_FROM_ADDRESS,
    EMAIL_FROM_NAME,
)


class EmailServiceError(Exception):
    """
    Error producido durante el envío de correo.
    """


def validar_configuracion_email() -> None:
    """
    Verifica que existan los datos mínimos para enviar correo.
    """
    faltantes: list[str] = []

    if not BREVO_API_KEY:
        faltantes.append("BREVO_API_KEY")

    if not EMAIL_FROM_ADDRESS:
        faltantes.append("EMAIL_FROM")

    if faltantes:
        raise EmailServiceError(
            "Falta configurar: "
            + ", ".join(faltantes)
        )


def _construir_payload(
    *,
    destinatario: str,
    asunto: str,
    contenido_texto: str,
    contenido_html: str | None = None,
) -> dict:
    """
    Construye el cuerpo requerido por la API transaccional
    de Brevo.
    """
    payload: dict = {
        "sender": {
            "name": EMAIL_FROM_NAME,
            "email": EMAIL_FROM_ADDRESS,
        },
        "to": [
            {
                "email": destinatario,
            }
        ],
        "subject": asunto,
    }

    if contenido_html:
        payload["htmlContent"] = contenido_html
    else:
        payload["textContent"] = contenido_texto

    return payload


def enviar_correo(
    *,
    destinatario: str,
    asunto: str,
    contenido_texto: str,
    contenido_html: str | None = None,
) -> None:
    """
    Envía un correo transaccional mediante la API de Brevo.

    Mantiene la misma interfaz utilizada actualmente por los
    servicios de verificación de correo y recuperación de
    contraseña.
    """
    validar_configuracion_email()

    url = (
        f"{BREVO_API_BASE_URL}/smtp/email"
    )

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    payload = _construir_payload(
        destinatario=destinatario,
        asunto=asunto,
        contenido_texto=contenido_texto,
        contenido_html=contenido_html,
    )

    try:
        respuesta = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=BREVO_API_TIMEOUT,
        )

    except requests.RequestException as exc:
        raise EmailServiceError(
            "No fue posible comunicarse con el "
            "servicio de correo electrónico."
        ) from exc

    if not 200 <= respuesta.status_code < 300:
        raise EmailServiceError(
            "El servicio de correo rechazó el envío "
            f"(HTTP {respuesta.status_code})."
        )