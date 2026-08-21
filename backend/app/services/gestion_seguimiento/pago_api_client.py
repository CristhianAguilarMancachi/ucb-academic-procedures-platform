from __future__ import annotations

from urllib.parse import urljoin

import requests
from pydantic import ValidationError

from app.core.config import (
    PAGO_API_BASE_URL,
    PAGO_API_TIMEOUT,
    PAGO_API_TOKEN,
    PAGO_API_VALIDAR_PATH,
)
from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoApiRespuesta,
    PagoApiValidarRequest,
)


class PagoApiClientError(Exception):
    """Error base de comunicación con la API de pagos."""


class PagoApiConexionError(
    PagoApiClientError
):
    """No fue posible establecer comunicación con la API."""


class PagoApiRespuestaInvalidaError(
    PagoApiClientError
):
    """La API respondió con un contrato inesperado."""


def _construir_url() -> str:
    """
    Construye la URL a partir de configuración externa.

    No existe ninguna URL de proveedor hardcodeada
    dentro del cliente.
    """
    return urljoin(
        PAGO_API_BASE_URL.rstrip("/") + "/",
        PAGO_API_VALIDAR_PATH.lstrip("/"),
    )


def _construir_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if PAGO_API_TOKEN:
        headers[
            "Authorization"
        ] = f"Bearer {PAGO_API_TOKEN}"

    return headers


def validar_factura(
    datos: PagoApiValidarRequest,
) -> PagoApiRespuesta:
    """
    Consulta la API externa de facturación.

    Contrato lógico enviado actualmente:

        codigo
        numero_factura

    El service de negocio no conoce HTTP, URLs,
    autenticación ni formato externo.

    Cuando exista la API institucional real:

    - si mantiene este contrato, bastará cambiar
      configuración;
    - si utiliza otro contrato, este cliente será
      el único punto que deberá adaptarlo.
    """
    try:
        response = requests.post(
            _construir_url(),
            json=datos.model_dump(
                mode="json"
            ),
            headers=_construir_headers(),
            timeout=PAGO_API_TIMEOUT,
        )

    except requests.Timeout as exc:
        raise PagoApiConexionError(
            "La API de pagos excedió el tiempo "
            "máximo de respuesta."
        ) from exc

    except requests.ConnectionError as exc:
        raise PagoApiConexionError(
            "No fue posible establecer conexión "
            "con la API de pagos."
        ) from exc

    except requests.RequestException as exc:
        raise PagoApiConexionError(
            "Ocurrió un error al comunicarse "
            "con la API de pagos."
        ) from exc

    if not response.ok:
        raise PagoApiConexionError(
            "La API de pagos respondió con "
            f"HTTP {response.status_code}."
        )

    try:
        contenido = response.json()

    except ValueError as exc:
        raise PagoApiRespuestaInvalidaError(
            "La API de pagos no devolvió "
            "una respuesta JSON válida."
        ) from exc

    try:
        return PagoApiRespuesta.model_validate(
            contenido
        )

    except ValidationError as exc:
        raise PagoApiRespuestaInvalidaError(
            "La respuesta recibida desde la API "
            "de pagos no cumple el contrato esperado."
        ) from exc