from __future__ import annotations

import smtplib

from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import (
    EMAIL_FROM_ADDRESS,
    EMAIL_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_USE_SSL,
    SMTP_USE_TLS,
)


class EmailServiceError(Exception):
    """
    Error producido durante el envío de correo.
    """


def validar_configuracion_email() -> None:
    """
    Verifica que existan los datos mínimos para enviar correo.
    """
    faltantes = []

    if not SMTP_HOST:
        faltantes.append("SMTP_HOST")

    if not EMAIL_FROM_ADDRESS:
        faltantes.append("EMAIL_FROM_ADDRESS")

    if faltantes:
        raise EmailServiceError(
            "Falta configurar: "
            + ", ".join(faltantes)
        )


def construir_mensaje(
    *,
    destinatario: str,
    asunto: str,
    contenido_texto: str,
    contenido_html: str | None = None,
) -> EmailMessage:
    """
    Construye un correo multipart con versión de texto y HTML.
    """
    mensaje = EmailMessage()

    mensaje["From"] = formataddr(
        (
            EMAIL_FROM_NAME,
            EMAIL_FROM_ADDRESS,
        )
    )
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto

    mensaje.set_content(
        contenido_texto,
    )

    if contenido_html:
        mensaje.add_alternative(
            contenido_html,
            subtype="html",
        )

    return mensaje


def enviar_correo(
    *,
    destinatario: str,
    asunto: str,
    contenido_texto: str,
    contenido_html: str | None = None,
) -> None:
    """
    Envía un correo mediante el servidor SMTP configurado.
    """
    validar_configuracion_email()

    mensaje = construir_mensaje(
        destinatario=destinatario,
        asunto=asunto,
        contenido_texto=contenido_texto,
        contenido_html=contenido_html,
    )

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(
                SMTP_HOST,
                SMTP_PORT,
                timeout=20,
            ) as servidor:
                if SMTP_USERNAME:
                    servidor.login(
                        SMTP_USERNAME,
                        SMTP_PASSWORD,
                    )

                servidor.send_message(mensaje)

            return

        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20,
        ) as servidor:
            servidor.ehlo()

            if SMTP_USE_TLS:
                servidor.starttls()
                servidor.ehlo()

            if SMTP_USERNAME:
                servidor.login(
                    SMTP_USERNAME,
                    SMTP_PASSWORD,
                )

            servidor.send_message(mensaje)

    except (
        smtplib.SMTPException,
        OSError,
    ) as exc:
        raise EmailServiceError(
            "No fue posible enviar el correo electrónico."
        ) from exc