"""Pruebas de integración controlada del módulo M03.

Verifican:
- contrato HTTP con la API simulada de pagos;
- validación de respuestas;
- recuperación del documento de identidad;
- declaración física del solicitante;
- envío de solicitud con el modelo actual.

No utiliza PostgreSQL real.
"""

import os
import unittest
from contextlib import ExitStack
from decimal import Decimal
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import requests
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine

from mock_pago_api import main as mock_api

from app.services.gestion_seguimiento import (
    datos_pago_service as identidad,
    pago_api_client as cliente,
    pago_verificacion_service as pago,
    seguimiento_service as seguimiento,
    solicitud_service as envio,
)

from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoApiValidarRequest,
)


@event.listens_for(Engine, "do_connect")
def prohibir_postgresql(*args):
    raise AssertionError(
        "PostgreSQL real está prohibido en estas pruebas."
    )


class ContratoPagoTest(unittest.TestCase):

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(
            self.stack.close
        )

        self.stack.enter_context(
            patch.dict(
                os.environ,
                {
                    "MOCK_PAGO_API_TOKEN": ""
                },
            )
        )

        mock_api.inicializar_base_datos()

        self.http = self.stack.enter_context(
            TestClient(
                mock_api.app
            )
        )

        def post(
            url,
            *,
            json,
            headers,
            timeout,
        ):
            respuesta = self.http.post(
                "/api/v1/facturas/validar",
                json=json,
                headers=headers,
            )

            return NS(
                ok=respuesta.is_success,
                status_code=respuesta.status_code,
                json=respuesta.json,
            )

        self.transporte = (
            self.stack.enter_context(
                patch.object(
                    cliente.requests,
                    "post",
                    side_effect=post,
                )
            )
        )

    def consultar(
        self,
        factura,
        **cambios,
    ):
        datos = {
            "codigo":
                "MOCK-CERT-CONCLUSION-001",
            "documento_identidad":
                "1234567",
            "numero_factura":
                factura,
            **cambios,
        }

        return cliente.validar_factura(
            PagoApiValidarRequest(
                **datos
            )
        )

    def evaluar(
        self,
        respuesta,
    ):
        return pago._evaluar_respuesta_api(
            respuesta=respuesta,
            numero_factura_esperado=(
                respuesta.numero_factura
            ),
            codigo_esperado=(
                "MOCK-CERT-CONCLUSION-001"
            ),
            documento_esperado="1234567",
            monto_esperado=Decimal(
                "55.00"
            ),
            moneda_esperada="BOB",
        )[0]

    def test_health_y_factura_valida(self):
        self.assertEqual(
            self.http.get(
                "/health"
            ).json(),
            {
                "status": "ok"
            },
        )

        primera = self.consultar(
            "26010001",
            codigo="MOCK-TITULO-001",
        )

        segunda = self.consultar(
            "26010001",
            codigo="MOCK-TITULO-001",
        )

        self.assertTrue(
            primera.encontrada
        )

        self.assertEqual(
            primera.estado_factura,
            "pagada",
        )

        self.assertFalse(
            primera.utilizada
        )

        self.assertEqual(
            primera,
            segunda,
        )

        enviado = (
            self.transporte
            .call_args
            .kwargs["json"]
        )

        self.assertEqual(
            enviado[
                "documento_identidad"
            ],
            "1234567",
        )

        self.assertEqual(
            enviado["codigo"],
            "MOCK-TITULO-001",
        )

    def test_discrepancias_no_acreditan(self):
        casos = (
            "INEXISTENTE",
            "CI",
            "CODIGO",
            "MONTO",
            "MONEDA",
            "PENDIENTE",
            "UTILIZADA",
        )

        for caso in casos:
            with self.subTest(
                caso=caso
            ):
                resultado = self.consultar(
                    "FAC-PRUEBA-"
                    + caso
                )

                self.assertFalse(
                    self.evaluar(
                        resultado
                    )
                )

    def test_errores_transporte_son_controlados(self):
        for error in (
            requests.Timeout(),
            requests.ConnectionError(),
        ):
            with self.subTest(
                error=type(error).__name__
            ):
                self.transporte.side_effect = error

                with self.assertRaises(
                    cliente.PagoApiConexionError
                ):
                    self.consultar(
                        "FAC-PRUEBA-VALIDA"
                    )

    def test_respuesta_incompleta_no_se_acredita(self):
        self.transporte.side_effect = (
            None
        )

        self.transporte.return_value = NS(
            ok=True,
            status_code=200,
            json=lambda: {
                "encontrada": True,
                "numero_factura":
                    "F-1",
                "utilizada": False,
            },
        )

        with self.assertRaises(
            cliente
            .PagoApiRespuestaInvalidaError
        ):
            self.consultar(
                "F-1"
            )

    def test_ci_es_obligatorio(self):
        respuesta = self.http.post(
            "/api/v1/facturas/validar",
            json={
                "codigo": "COD",
                "numero_factura": "F-1",
            },
        )

        self.assertEqual(
            respuesta.status_code,
            422,
        )

    def test_token_del_mock_es_validado(self):
        with patch.dict(
            os.environ,
            {
                "MOCK_PAGO_API_TOKEN":
                    "solo-prueba"
            },
        ):
            respuesta = self.http.post(
                "/api/v1/facturas/validar",
                json={
                    "codigo": "COD",
                    "numero_factura":
                        "F-1",
                    "documento_identidad":
                        "1234567",
                },
            )

        self.assertEqual(
            respuesta.status_code,
            401,
        )


class IdentidadPagoTest(unittest.TestCase):

    def test_snapshot_prevalece_sobre_perfil(self):
        db = Mock()

        solicitud = NS(
            id_solicitud=1,
            id_solicitante=7,
        )

        with (
            patch.object(
                identidad.solicitud_repository,
                "listar_datos_solicitud",
                return_value=[
                    NS(
                        clave_snapshot=(
                            "documento_identidad"
                        ),
                        valor="1234567",
                        campo=None,
                    )
                ],
            ) as datos,
            patch.object(
                identidad.seguimiento_repository,
                "obtener_perfil",
                return_value=NS(
                    documento_identidad=(
                        "7654321"
                    )
                ),
            ) as perfil,
        ):
            self.assertEqual(
                identidad.obtener_documento_pago(
                    db,
                    solicitud,
                ),
                "1234567",
            )

            perfil.assert_not_called()

            datos.return_value = []

            self.assertEqual(
                identidad.obtener_documento_pago(
                    db,
                    solicitud,
                ),
                "7654321",
            )

            perfil.return_value = None

            self.assertIsNone(
                identidad.obtener_documento_pago(
                    db,
                    solicitud,
                )
            )


class DeclaracionFisicaTest(unittest.TestCase):

    def setUp(self):
        self.db = Mock()

        self.requisito = NS(
            id_solicitud_requisito=1,
            id_solicitud=1,
            nombre="Documento",
            requiere_presentacion_fisica=True,
            presentado=False,
        )

        self.solicitud = NS(
            id_solicitud=1,
            id_solicitante=7,
            estado="pendiente_recepcion",
            requisitos=[
                self.requisito
            ],
        )

        self.stack = ExitStack()
        self.addCleanup(
            self.stack.close
        )

        self.stack.enter_context(
            patch.object(
                seguimiento.repo,
                "bloquear_solicitud",
                return_value=self.solicitud,
            )
        )

        self.stack.enter_context(
            patch.object(
                seguimiento.repo,
                "obtener_solicitud_completa",
                return_value=self.solicitud,
            )
        )

        self.historial = (
            self.stack.enter_context(
                patch.object(
                    seguimiento.repo,
                    "listar_historial",
                    return_value=[],
                )
            )
        )

        self.evento = (
            self.stack.enter_context(
                patch.object(
                    seguimiento,
                    "evento",
                )
            )
        )

    def test_declaracion_no_equivale_a_recepcion(self):
        seguimiento.declarar_entrega_fisica(
            self.db,
            1,
            1,
            7,
        )

        self.assertFalse(
            self.requisito.presentado
        )

        self.evento.assert_called_once()

    def test_declaracion_repetida_no_duplica_evento(self):
        seguimiento.declarar_entrega_fisica(
            self.db,
            1,
            1,
            7,
        )

        self.historial.return_value = [
            NS(
                evento=(
                    "entrega_fisica_declarada"
                ),
                id_solicitud_requisito=1,
            )
        ]

        seguimiento.declarar_entrega_fisica(
            self.db,
            1,
            1,
            7,
        )

        self.evento.assert_called_once()

    def test_otro_propietario_es_rechazado(self):
        with self.assertRaises(
            seguimiento.SeguimientoError
        ):
            seguimiento.declarar_entrega_fisica(
                self.db,
                1,
                1,
                8,
            )

    def test_estado_cerrado_es_rechazado(self):
        self.solicitud.estado = (
            "finalizada"
        )

        with self.assertRaises(
            seguimiento.SeguimientoError
        ):
            seguimiento.declarar_entrega_fisica(
                self.db,
                1,
                1,
                7,
            )

    def test_requisito_no_fisico_es_rechazado(self):
        self.requisito.requiere_presentacion_fisica = (
            False
        )

        with self.assertRaises(
            seguimiento.SeguimientoError
        ):
            seguimiento.declarar_entrega_fisica(
                self.db,
                1,
                1,
                7,
            )


class EnvioActualTest(unittest.TestCase):

    def test_envio_no_recibe_facturas_ni_etapas(self):
        db = Mock()

        solicitud = NS(
            id_solicitud=1,
            id_solicitante=7,
            id_tramite=1,
            estado="borrador",
            nombre_contacto="Daniel",
            telefono_contacto="77777777",
            correo_contacto="daniel@example.com",
            nombre_tramite_snapshot=None,
            tipo_finalizacion=None,
            tipo_intervencion="ninguna",
        )

        tramite = NS(
            nombre="Trámite",
            tipo_finalizacion=(
                "resultado_registrado"
            ),
            tipo_intervencion="ninguna",
        )

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    envio,
                    "_obtener_solicitud_del_usuario",
                    return_value=solicitud,
                )
            )

            stack.enter_context(
                patch.object(
                    envio,
                    "_obtener_tramite_habilitado",
                    return_value=tramite,
                )
            )

            stack.enter_context(
                patch.object(
                    envio,
                    "_obtener_perfil_minimo",
                    return_value={
                        "carrera_programa":
                            "Ingeniería de Sistemas",
                        "documento_identidad":
                            "1234567",
                    },
                )
            )

            stack.enter_context(
                patch.object(
                    envio,
                    "validar_flujo_envio",
                )
            )

            stack.enter_context(
                patch.object(
                    envio,
                    "requisitos_aplicables",
                    return_value=[],
                )
            )

            stack.enter_context(
                patch.object(
                    envio,
                    "_obtener_respuesta_completa",
                    return_value=solicitud,
                )
            )

            stack.enter_context(
                patch.object(
                    envio.tramite_repository,
                    "listar_campos_tramite",
                    return_value=[],
                )
            )

            stack.enter_context(
                patch.object(
                    envio.tramite_repository,
                    "listar_requisitos_tramite",
                    return_value=[],
                )
            )

            stack.enter_context(
                patch.object(
                    envio.solicitud_repository,
                    "listar_datos_solicitud",
                    return_value=[],
                )
            )

            stack.enter_context(
                patch.object(
                    envio.solicitud_repository,
                    "contar_requisitos_solicitud",
                    return_value=0,
                )
            )

            stack.enter_context(
                patch.object(
                    envio.solicitud_repository,
                    "marcar_solicitud_enviada",
                )
            )

            stack.enter_context(
                patch.object(
                    envio,
                    "registrar_accion_simple",
                )
            )

            historial = (
                stack.enter_context(
                    patch.object(
                        envio.seguimiento_repo,
                        "registrar_historial",
                    )
                )
            )

            resultado = envio.enviar_solicitud(
                db,
                id_solicitud=1,
                id_solicitante=7,
            )

        self.assertIs(
            resultado,
            solicitud,
        )

        self.assertEqual(
            solicitud.nombre_tramite_snapshot,
            "Trámite",
        )

        self.assertEqual(
            solicitud.tipo_finalizacion,
            "resultado_registrado",
        )

        historial.assert_called_once()
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
