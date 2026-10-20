
from __future__ import annotations

from html import escape
from urllib.parse import urlsplit

import requests

from app.core.config import (
    BREVO_API_BASE_URL,
    BREVO_API_KEY,
    BREVO_API_TIMEOUT,
    EMAIL_FROM_ADDRESS,
    EMAIL_FROM_NAME,
)


class EmailServiceError(Exception):
    """Error producido durante el envío de correo."""


def validar_configuracion_email() -> None:
    faltantes: list[str] = []

    if not BREVO_API_KEY:
        faltantes.append("BREVO_API_KEY")

    if not EMAIL_FROM_ADDRESS:
        faltantes.append("EMAIL_FROM")

    if faltantes:
        raise EmailServiceError(
            "Falta configurar: " + ", ".join(faltantes)
        )


def construir_html_institucional(
    *,
    titulo: str,
    parrafos: list[str],
    texto_accion: str | None = None,
    url_accion: str | None = None,
    referencia: str | None = None,
    aviso: str | None = None,
) -> str:
    """
    Plantilla HTML común para los correos del sistema.

    Escapa los contenidos recibidos, utiliza estilos inline
    compatibles con clientes de correo y no incorpora
    imágenes ni recursos externos.

    Los textos pueden contener saltos de línea.
    """

    if url_accion is not None:
        partes = urlsplit(url_accion)
        if (
            partes.scheme not in {"https", "http"}
            or not partes.netloc
        ):
            raise ValueError(
                "El enlace del correo debe utilizar HTTP o HTTPS."
            )

    def html_texto(valor: str) -> str:
        return escape(valor).replace("\n", "<br>")

    bloques = "".join(
        (
            '<p style="margin:0 0 16px;'
            'font-size:15px;line-height:1.7;'
            'color:#334155;">'
            f'{html_texto(parrafo)}'
            '</p>'
        )
        for parrafo in parrafos
    )

    bloque_referencia = ""
    if referencia:
        bloque_referencia = (
            '<div style="margin:0 0 22px;padding:13px 16px;'
            'background-color:#F1F5F9;'
            'border-left:4px solid #FFCD00;">'
            '<p style="margin:0;color:#334155;'
            'font-size:14px;line-height:1.6;">'
            f'{html_texto(referencia)}'
            '</p></div>'
        )

    bloque_accion = ""
    if url_accion and texto_accion:
        url_segura = escape(url_accion, quote=True)
        bloque_accion = (
            '<div style="margin:26px 0;text-align:center;">'
            f'<a href="{url_segura}" '
            'style="display:inline-block;'
            'background-color:#003B70;'
            'border-radius:6px;padding:13px 22px;'
            'font-size:15px;font-weight:700;'
            'line-height:1.4;color:#FFFFFF;'
            'text-decoration:none;">'
            f'{escape(texto_accion)}'
            '</a></div>'
            '<p style="margin:0 0 18px;'
            'font-size:12px;line-height:1.6;'
            'color:#64748B;overflow-wrap:anywhere;">'
            'Si el botón no funciona, abre este enlace:'
            '<br>'
            f'<a href="{url_segura}" '
            'style="color:#005A9C;">'
            f'{escape(url_accion)}'
            '</a></p>'
        )

    bloque_aviso = ""
    if aviso:
        bloque_aviso = (
            '<p style="margin:18px 0 0;'
            'padding-top:14px;'
            'border-top:1px solid #E2E8F0;'
            'font-size:13px;line-height:1.6;'
            'color:#64748B;">'
            f'{html_texto(aviso)}'
            '</p>'
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport"
        content="width=device-width, initial-scale=1">
  <title>{escape(titulo)}</title>
</head>
<body style="margin:0;padding:0;
             background-color:#F1F5F9;
             font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation"
         cellpadding="0"
         cellspacing="0"
         border="0"
         width="100%"
         style="background-color:#F1F5F9;">
    <tr>
      <td align="center" style="padding:28px 12px;">
        <table role="presentation"
               cellpadding="0"
               cellspacing="0"
               border="0"
               width="100%"
               style="max-width:600px;
                      background-color:#FFFFFF;
                      border-radius:8px;
                      overflow:hidden;">
          <tr>
            <td style="background-color:#003B70;
                       border-top:5px solid #FFCD00;
                       padding:26px 30px;">
              <p style="margin:0 0 7px;
                        font-size:12px;
                        font-weight:700;
                        letter-spacing:1px;
                        color:#FFCD00;">
                UCB · SEDE LA PAZ
              </p>
              <p style="margin:0;
                        color:#FFFFFF;
                        font-size:20px;
                        font-weight:700;
                        line-height:1.35;">
                Sistema de Trámites Académicos
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:30px;">
              <h1 style="margin:0 0 22px;
                         color:#003B70;
                         font-size:23px;
                         line-height:1.35;">
                {escape(titulo)}
              </h1>
              {bloque_referencia}
              {bloques}
              {bloque_accion}
              {bloque_aviso}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 30px;
                       background-color:#F8FAFC;
                       border-top:1px solid #E2E8F0;">
              <p style="margin:0;
                        font-size:12px;
                        line-height:1.6;
                        color:#64748B;">
                Universidad Católica Boliviana
                «San Pablo» — Sede La Paz.
                <br>
                Mensaje automático del Sistema de
                Trámites Académicos.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _construir_payload(
    *,
    destinatario: str,
    asunto: str,
    contenido_texto: str,
    contenido_html: str | None = None,
) -> dict:
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
        "textContent": contenido_texto,
    }

    if contenido_html:
        payload["htmlContent"] = contenido_html

    return payload


def enviar_correo(
    *,
    destinatario: str,
    asunto: str,
    contenido_texto: str,
    contenido_html: str | None = None,
) -> None:
    """
    Envía un correo transaccional utilizando Brevo.

    Una respuesta HTTP exitosa indica aceptación por Brevo,
    no garantiza su entrega al destinatario.
    """

    validar_configuracion_email()

    url = f"{BREVO_API_BASE_URL}/smtp/email"

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
