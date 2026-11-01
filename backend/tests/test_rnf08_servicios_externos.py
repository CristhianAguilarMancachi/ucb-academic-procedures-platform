"""
RNF-08 — Disponibilidad y manejo de fallos de servicios externos.

Estas pruebas verifican que los proveedores externos utilizados por el
sistema puedan fallar de forma controlada sin necesidad de contactar
servicios reales.

Servicios evaluados:

EXT-01 — Jina AI / embeddings
EXT-02 — Groq / generación LLM
EXT-03 — Brevo / correo electrónico
EXT-04 — API externa simulada de pagos

Las pruebas utilizan mocks y no realizan peticiones reales a Internet.
"""

import unittest
from unittest.mock import Mock, patch

import httpx
import requests

from groq import APITimeoutError

from app.services.rag import embeddings
from app.services.rag import llm_client as llm
from app.services.rag.generator import generate_answer

from app.services.email import email_service as email

from app.services.gestion_seguimiento import (
    pago_api_client as pago_cliente,
)

from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoApiValidarRequest,
)


class RNF08ServiciosExternosTests(unittest.TestCase):
    """
    Pruebas aisladas para RNF-08.

    Ninguna prueba debe depender de la disponibilidad real de
    Jina, Groq, Brevo o de la API de facturación.
    """

    def test_ext01_jina_timeout_es_controlado(self):
        """
        EXT-01.

        Si Jina excede el tiempo de respuesta, el sistema debe
        convertir el error de red en JinaEmbeddingError.

        No deben generarse embeddings ficticios ni continuar como
        si la operación hubiese sido exitosa.
        """

        with (
            patch.object(
                embeddings,
                "JINA_MAX_RETRIES",
                0,
            ),
            patch.object(
                embeddings._session,
                "post",
                side_effect=requests.Timeout(
                    "Timeout simulado de Jina"
                ),
            ) as solicitud,
        ):
            with self.assertRaises(
                embeddings.JinaEmbeddingError
            ) as error:
                embeddings.generate_query_embeddings(
                    ["Consulta de prueba para RNF-08"]
                )

        self.assertIn(
            "Jina",
            str(error.exception),
        )

        solicitud.assert_called_once()

    def test_ext02_groq_timeout_es_controlado(self):
        """
        EXT-02.

        Si Groq no responde, el SDK no debe propagar detalles
        internos al resto del sistema.

        Debe convertirse en LLMUnavailableError utilizando el
        mensaje controlado definido por la aplicación.
        """

        cliente = Mock()

        cliente.chat.completions.create.side_effect = (
            APITimeoutError(
                request=httpx.Request(
                    "POST",
                    "https://example.invalid",
                )
            )
        )

        metadatas = [
            {
                "titulo": "Documento institucional de prueba",
                "pagina_inicio": 1,
                "pagina_fin": 1,
                "articulo_numero": None,
                "seccion": None,
                "subseccion": None,
            }
        ]

        with patch.object(
            llm,
            "get_client",
            return_value=cliente,
        ):
            with self.assertRaises(
                llm.LLMUnavailableError
            ) as error:
                generate_answer(
                    "Pregunta de prueba",
                    ["Contexto institucional de prueba"],
                    metadatas,
                )

        self.assertEqual(
            str(error.exception),
            llm.UNAVAILABLE_MESSAGE,
        )

        cliente.chat.completions.create.assert_called_once()

    def test_ext03_brevo_timeout_es_controlado(self):
        """
        EXT-03.

        Si Brevo no responde, la capa de correo debe transformar
        el timeout de requests en un error propio del servicio.

        No se utiliza ninguna API real.
        """

        with (
            patch.object(
                email,
                "validar_configuracion_email",
                return_value=None,
            ),
            patch.object(
                email.requests,
                "post",
                side_effect=requests.Timeout(
                    "Timeout simulado de Brevo"
                ),
            ) as solicitud,
        ):
            with self.assertRaises(
                email.EmailServiceError
            ):
                email.enviar_correo(
                    destinatario="prueba@example.com",
                    asunto="Prueba RNF-08",
                    contenido_texto=(
                        "Correo generado únicamente "
                        "para una prueba automatizada."
                    ),
                )

        solicitud.assert_called_once()

    def test_ext04_api_pago_timeout_es_controlado(self):
        """
        EXT-04.

        Si la API externa de pagos excede el tiempo de respuesta,
        el cliente debe devolver PagoApiConexionError en lugar de
        considerar el pago como válido.
        """

        datos = PagoApiValidarRequest(
            codigo="MOCK-CERT-CONCLUSION-001",
            documento_identidad="1234567",
            numero_factura="FAC-RNF08-001",
        )

        with patch.object(
            pago_cliente.requests,
            "post",
            side_effect=requests.Timeout(
                "Timeout simulado de API de pagos"
            ),
        ) as solicitud:
            with self.assertRaises(
                pago_cliente.PagoApiConexionError
            ):
                pago_cliente.validar_factura(
                    datos
                )

        solicitud.assert_called_once()


if __name__ == "__main__":
    unittest.main()