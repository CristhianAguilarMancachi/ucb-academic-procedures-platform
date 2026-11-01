"""Pruebas unitarias del flujo actual de gestión y seguimiento.

No utilizan PostgreSQL ni proveedores externos reales.
El flujo vigente se basa en:
- recepción e inicio de atención;
- requisitos;
- observaciones;
- intervención presencial cuando corresponde;
- resultado administrativo;
- pagos.
"""

from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.models.gestion_seguimiento import (
    SolicitudObservacion,
    SolicitudResultado,
)

from app.services.gestion_seguimiento import (
    atencion_service as atencion,
    configuracion_flujo_service as reglas,
    intervencion_service as intervencion,
    pago_verificacion_service as pago,
    seguimiento_service as svc,
    solicitud_administrativa_service as admin,
    solicitud_service as envio,
)

from app.schemas.gestion_seguimiento.intervencion import (
    RevisionPresencialRequest,
)

from app.schemas.gestion_seguimiento.seguimiento import (
    ObservacionCrearRequest,
    ResultadoRegistrarRequest,
)

from app.schemas.gestion_seguimiento.solicitud_administrativa import (
    RequisitosAdministrativosConfirmarRequest,
)

from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoApiRespuesta,
)


@event.listens_for(Engine, "do_connect")
def prohibir_conexion(*args):
    raise AssertionError(
        "Estas pruebas no pueden conectar a PostgreSQL."
    )


def requisito(**cambios):
    datos = dict(
        id_solicitud_requisito=1,
        id_solicitud=1,
        nombre="Requisito",
        obligatorio=True,
        orden=1,
        requiere_presentacion_fisica=False,
        presentado=False,
        fecha_presentacion=None,
        id_usuario_presentacion=None,
        estado_verificacion="pendiente",
        id_usuario_verificador=None,
        fecha_verificacion=None,
        detalle_verificacion=None,
        fecha_actualizacion=None,
        es_economico=False,
        numero_factura=None,
        codigo_concepto_externo=None,
        monto_economico=None,
        moneda=None,
    )

    datos.update(cambios)
    return NS(**datos)


class SeguimientoActualTest(unittest.TestCase):

    def setUp(self):
        self.db = Mock()

        self.s = NS(
            id_solicitud=1,
            id_solicitante=7,
            estado="en_proceso",
            requisitos=[],
            tipo_finalizacion="resultado_registrado",
            tipo_intervencion="ninguna",
            fecha_actualizacion=None,
            nombre_tramite_snapshot="Trámite",
            tramite=NS(
                nombre="Trámite",
                tipo_intervencion="ninguna",
            ),
        )

        self.observaciones = []
        self.pagos = []
        self.registros = []

        self.db.add.side_effect = self.registros.append

        self.stack = ExitStack()
        self.addCleanup(self.stack.close)

        self.stack.enter_context(
            patch.object(
                svc.repo,
                "bloquear_solicitud",
                return_value=self.s,
            )
        )

        self.stack.enter_context(
            patch.object(
                svc.repo,
                "obtener_solicitud_completa",
                return_value=self.s,
            )
        )

        self.stack.enter_context(
            patch.object(
                svc.repo,
                "listar_observaciones",
                side_effect=lambda *a, **k: self.observaciones,
            )
        )

        self.stack.enter_context(
            patch.object(
                svc.repo,
                "listar_pagos",
                side_effect=lambda *a, **k: self.pagos,
            )
        )

        self.stack.enter_context(
            patch.object(
                svc.repo,
                "obtener_resultado",
                side_effect=lambda *a, **k: next(
                    (
                        item
                        for item in self.registros
                        if isinstance(
                            item,
                            SolicitudResultado,
                        )
                    ),
                    None,
                ),
            )
        )

        self.stack.enter_context(
            patch.object(
                svc,
                "obtener_documento_pago",
                return_value="1234567",
            )
        )

        self.stack.enter_context(
            patch.object(
                svc,
                "registrar_accion_simple",
            )
        )

        self.evento = self.stack.enter_context(
            patch.object(
                svc,
                "evento",
            )
        )

        self.atencion_evento = self.stack.enter_context(
            patch.object(
                atencion,
                "evento",
            )
        )

        self.stack.enter_context(
            patch.object(
                atencion,
                "exigir_intervencion_completada",
                return_value=None,
            )
        )

    def test_cancelacion_antes_de_recepcion(self):
        for estado in (
            "borrador",
            "pendiente_recepcion",
        ):
            with self.subTest(estado=estado):
                self.s.estado = estado
                self.s.requisitos = []
                self.pagos.clear()

                svc.cancelar(
                    self.db,
                    1,
                    7,
                    "Trámite incorrecto",
                )

                self.assertEqual(
                    self.s.estado,
                    "cancelada",
                )

        self.s.estado = "en_proceso"

        with self.assertRaises(
            svc.SeguimientoError
        ):
            svc.cancelar(
                self.db,
                1,
                7,
                "Motivo",
            )

    def test_cancelacion_bloqueada_por_factura_o_pago(self):
        self.s.estado = "pendiente_recepcion"

        self.s.requisitos = [
            requisito(
                numero_factura="F-1"
            )
        ]

        with self.assertRaises(
            svc.SeguimientoError
        ):
            svc.cancelar(
                self.db,
                1,
                7,
                "Motivo",
            )

        self.s.requisitos = []

        self.pagos[:] = [
            NS(
                estado="verificado"
            )
        ]

        with self.assertRaises(
            svc.SeguimientoError
        ):
            svc.cancelar(
                self.db,
                1,
                7,
                "Motivo",
            )

    def test_propietario_no_modifica_solicitud_ajena(self):
        self.s.estado = "pendiente_recepcion"

        with self.assertRaises(
            svc.SeguimientoError
        ) as exc:
            svc.cancelar(
                self.db,
                1,
                99,
                "Motivo",
            )

        self.assertEqual(
            exc.exception.status_code,
            404,
        )

    def test_recepcion_fisica_confirma_requisito(self):
        r = requisito(
            requiere_presentacion_fisica=True,
        )

        self.s.requisitos = [r]
        self.s.estado = "en_proceso"

        svc.registrar_presentacion(
            self.db,
            1,
            1,
            8,
        )

        self.assertTrue(r.presentado)

        self.assertEqual(
            r.estado_verificacion,
            "cumple",
        )

        self.assertEqual(
            r.id_usuario_presentacion,
            8,
        )

        self.assertEqual(
            r.id_usuario_verificador,
            8,
        )

        self.evento.assert_called_once()

        # Idempotencia.
        svc.registrar_presentacion(
            self.db,
            1,
            1,
            8,
        )

        self.evento.assert_called_once()

    def test_recepcion_fisica_rechaza_requisito_no_fisico(self):
        self.s.requisitos = [
            requisito(
                requiere_presentacion_fisica=False,
            )
        ]

        with self.assertRaises(
            svc.SeguimientoError
        ) as exc:
            svc.registrar_presentacion(
                self.db,
                1,
                1,
                8,
            )

        self.assertEqual(
            exc.exception.status_code,
            400,
        )

    def test_observacion_se_registra_y_resuelve(self):
        datos = ObservacionCrearRequest(
            detalle="Falta documento.",
            correccion_requerida=(
                "Presentar el documento original."
            ),
        )

        svc.crear_observacion(
            self.db,
            1,
            8,
            datos,
        )

        observacion = next(
            item
            for item in self.registros
            if isinstance(
                item,
                SolicitudObservacion,
            )
        )

        observacion.id_observacion = 5

        self.observaciones.append(
            observacion
        )

        self.assertEqual(
            observacion.estado,
            "pendiente",
        )

        svc.resolver_observacion(
            self.db,
            1,
            5,
            8,
        )

        self.assertEqual(
            observacion.estado,
            "resuelta",
        )

        self.assertEqual(
            observacion.id_usuario_resolucion,
            8,
        )

    def test_observacion_pendiente_bloquea_resultado(self):
        self.observaciones.append(
            NS(
                estado="pendiente"
            )
        )

        with self.assertRaises(
            svc.SeguimientoError
        ):
            atencion.registrar_resultado(
                self.db,
                1,
                8,
                ResultadoRegistrarRequest(
                    detalle="Resultado",
                ),
            )

    def test_requisito_obligatorio_bloquea_resultado(self):
        self.s.requisitos = [
            requisito(
                obligatorio=True,
                estado_verificacion="pendiente",
            )
        ]

        with self.assertRaises(
            svc.SeguimientoError
        ):
            atencion.registrar_resultado(
                self.db,
                1,
                8,
                ResultadoRegistrarRequest(
                    detalle="Resultado",
                ),
            )

    def test_resultado_registrado_finaliza_solicitud(self):
        self.s.estado = "en_proceso"
        self.s.requisitos = []
        self.s.tipo_finalizacion = (
            "resultado_registrado"
        )

        atencion.registrar_resultado(
            self.db,
            1,
            8,
            ResultadoRegistrarRequest(
                detalle="Aprobado",
            ),
        )

        self.assertEqual(
            self.s.estado,
            "finalizada",
        )

        resultados = [
            item
            for item in self.registros
            if isinstance(
                item,
                SolicitudResultado,
            )
        ]

        self.assertEqual(
            len(resultados),
            1,
        )

        self.assertEqual(
            resultados[0].tipo_finalizacion,
            "resultado_registrado",
        )

        with self.assertRaises(
            svc.SeguimientoError
        ):
            atencion.registrar_resultado(
                self.db,
                1,
                8,
                ResultadoRegistrarRequest(
                    detalle="Duplicado",
                ),
            )

    def test_resultado_entrega_deja_lista_para_recojo(self):
        self.s.estado = "en_proceso"
        self.s.requisitos = []
        self.s.tipo_finalizacion = "entrega"

        atencion.registrar_resultado(
            self.db,
            1,
            8,
            ResultadoRegistrarRequest(
                detalle="Documento disponible",
            ),
        )

        self.assertEqual(
            self.s.estado,
            "lista_para_entrega",
        )

    def test_no_se_puede_cambiar_modalidad_final(self):
        self.s.estado = "en_proceso"
        self.s.tipo_finalizacion = (
            "resultado_registrado"
        )

        with self.assertRaises(
            svc.SeguimientoError
        ):
            atencion.registrar_resultado(
                self.db,
                1,
                8,
                ResultadoRegistrarRequest(
                    detalle="Resultado",
                    tipo_finalizacion="entrega",
                ),
            )

    def test_rechazo_administrativo(self):
        self.s.estado = "en_proceso"

        svc.rechazar(
            self.db,
            1,
            8,
            "No corresponde.",
        )

        self.assertEqual(
            self.s.estado,
            "rechazada",
        )

    def test_registro_factura_y_proteccion_de_acreditada(self):
        r = requisito(
            es_economico=True,
            numero_factura=None,
        )

        self.s.estado = "en_proceso"
        self.s.requisitos = [r]

        svc.registrar_factura(
            self.db,
            1,
            1,
            7,
            "F-1",
        )

        self.assertEqual(
            r.numero_factura,
            "F-1",
        )

        self.assertEqual(
            r.estado_verificacion,
            "pendiente",
        )

        r.estado_verificacion = "cumple"

        with self.assertRaises(
            svc.SeguimientoError
        ):
            svc.registrar_factura(
                self.db,
                1,
                1,
                7,
                "F-2",
            )


class AtencionTest(unittest.TestCase):

    def test_iniciar_atencion_registra_recepcion_y_pasa_a_proceso(self):
        db = Mock()
        db.scalar.return_value = None

        solicitud = NS(
            id_solicitud=1,
            estado="pendiente_recepcion",
            tipo_intervencion="ninguna",
            fecha_actualizacion=None,
            tramite=NS(
                tipo_intervencion="conformidad"
            ),
        )

        with (
            patch.object(
                atencion,
                "obtener_para_accion",
                return_value=solicitud,
            ),
            patch.object(
                atencion,
                "evento",
            ) as evento,
        ):
            atencion.iniciar_atencion(
                db,
                1,
                8,
            )

        self.assertEqual(
            solicitud.estado,
            "en_proceso",
        )

        self.assertEqual(
            solicitud.tipo_intervencion,
            "conformidad",
        )

        self.assertEqual(
            db.add.call_count,
            1,
        )

        evento.assert_called_once()

        db.commit.assert_called_once()


class IntervencionTest(unittest.TestCase):

    def test_sin_intervencion_no_bloquea(self):
        solicitud = NS(
            id_solicitud=1,
            tipo_intervencion="ninguna",
        )

        intervencion.exigir_intervencion_completada(
            Mock(),
            solicitud,
        )

    def test_conformidad_debe_estar_completada_y_notificada(self):
        solicitud = NS(
            id_solicitud=1,
            tipo_intervencion="conformidad",
        )

        ultima = NS(
            id_intervencion=5,
            tipo="conformidad",
            estado="conforme",
        )

        with (
            patch.object(
                intervencion.intervenciones,
                "obtener_ultima",
                return_value=ultima,
            ),
            patch.object(
                intervencion.notificaciones,
                "obtener_convocatoria",
                return_value=NS(
                    estado="enviado"
                ),
            ),
        ):
            intervencion.exigir_intervencion_completada(
                Mock(),
                solicitud,
            )

    def test_conformidad_pendiente_bloquea_finalizacion(self):
        solicitud = NS(
            id_solicitud=1,
            tipo_intervencion="conformidad",
        )

        with patch.object(
            intervencion.intervenciones,
            "obtener_ultima",
            return_value=None,
        ):
            with self.assertRaises(
                svc.SeguimientoError
            ):
                intervencion.exigir_intervencion_completada(
                    Mock(),
                    solicitud,
                )

    def test_firma_exige_resolucion_previa(self):
        solicitud = NS(
            id_solicitud=1,
            tipo_intervencion="firma",
        )

        with patch.object(
            intervencion,
            "_buscar_resolucion",
            return_value=None,
        ):
            with self.assertRaises(
                svc.SeguimientoError
            ):
                intervencion.exigir_intervencion_completada(
                    Mock(),
                    solicitud,
                )


class AdministracionSolicitudTest(unittest.TestCase):

    def test_recibir_solicitud_delega_inicio_atencion(self):
        db = Mock()

        solicitud = NS(
            id_solicitud=1,
            estado="pendiente_recepcion",
        )

        detalle = NS()

        with (
            patch.object(
                admin,
                "_obtener_solicitud",
                return_value=solicitud,
            ),
            patch.object(
                admin.admin_repo,
                "obtener_recepcion_por_solicitud",
                return_value=None,
            ),
            patch.object(
                admin.atencion_service,
                "iniciar_atencion",
            ) as iniciar,
            patch.object(
                admin,
                "_construir_detalle",
                return_value=detalle,
            ),
        ):
            resultado = admin.recibir_solicitud(
                db,
                id_solicitud=1,
                id_usuario_receptor=8,
            )

        self.assertIs(
            resultado,
            detalle,
        )

        iniciar.assert_called_once_with(
            db,
            1,
            8,
        )

    def test_no_recibe_solicitud_ya_iniciada(self):
        db = Mock()

        with patch.object(
            admin,
            "_obtener_solicitud",
            return_value=NS(
                estado="en_proceso"
            ),
        ):
            with self.assertRaises(
                admin.SolicitudNoPendienteRecepcionError
            ):
                admin.recibir_solicitud(
                    db,
                    id_solicitud=1,
                    id_usuario_receptor=8,
                )

    def test_confirmacion_agrupada_requisitos_administrativos(self):
        db = Mock()

        r1 = requisito(
            id_solicitud_requisito=1,
            orden=1,
        )

        r2 = requisito(
            id_solicitud_requisito=2,
            orden=2,
        )

        solicitud = NS(
            id_solicitud=1,
            estado="en_proceso",
            requisitos=[
                r1,
                r2,
            ],
        )

        def actualizar(
            db,
            requisito,
            **datos,
        ):
            for campo, valor in datos.items():
                setattr(
                    requisito,
                    campo,
                    valor,
                )

            return requisito

        with (
            patch.object(
                admin.seguimiento_repo,
                "bloquear_solicitud",
            ),
            patch.object(
                admin,
                "_obtener_solicitud",
                return_value=solicitud,
            ),
            patch.object(
                admin,
                "validar_requisito_editable",
            ),
            patch.object(
                admin.admin_repo,
                "actualizar_verificacion_requisito",
                side_effect=actualizar,
            ),
            patch.object(
                admin.seguimiento_repo,
                "registrar_historial",
            ),
            patch.object(
                admin,
                "registrar_accion_simple",
            ),
        ):
            resultado = (
                admin.confirmar_requisitos_administrativos(
                    db,
                    id_solicitud=1,
                    id_usuario_verificador=8,
                    datos=(
                        RequisitosAdministrativosConfirmarRequest(
                            ids_requisitos=[
                                1,
                                2,
                            ]
                        )
                    ),
                )
            )

        self.assertEqual(
            resultado.cantidad_confirmada,
            2,
        )

        self.assertEqual(
            r1.estado_verificacion,
            "cumple",
        )

        self.assertEqual(
            r2.estado_verificacion,
            "cumple",
        )

        db.commit.assert_called_once()


class CondicionesTest(unittest.TestCase):

    def setUp(self):
        self.campo = NS(
            id_campo=1,
            clave="motivo",
            activo=True,
            tipo_dato="seleccion",
            etiqueta="Motivo",
            configuracion={
                "opciones": [
                    "extravío",
                    "otro",
                ]
            },
        )

        self.r = NS(
            condicion={
                "origen": "solicitud_dato",
                "clave": "motivo",
                "operador": "igual",
                "valor": "extravío",
            }
        )

    def test_condicion_filtra_segun_datos(self):
        with patch.object(
            reglas.seguimiento_repository,
            "obtener_perfil",
            return_value=None,
        ):
            self.assertEqual(
                reglas.requisitos_aplicables(
                    None,
                    NS(
                        id_solicitante=1
                    ),
                    [self.r],
                    [self.campo],
                    [
                        NS(
                            id_campo=1,
                            valor="extravío",
                        )
                    ],
                ),
                [self.r],
            )

            self.assertEqual(
                reglas.requisitos_aplicables(
                    None,
                    NS(
                        id_solicitante=1
                    ),
                    [self.r],
                    [self.campo],
                    [
                        NS(
                            id_campo=1,
                            valor="otro",
                        )
                    ],
                ),
                [],
            )

    def test_condicion_perfil(self):
        r = NS(
            condicion={
                "origen": "perfil_academico",
                "campo": "carrera_programa",
                "operador": "igual",
                "valor": "Enfermería",
            }
        )

        with patch.object(
            reglas.seguimiento_repository,
            "obtener_perfil",
            return_value=NS(
                carrera_programa="Enfermería"
            ),
        ):
            self.assertEqual(
                reglas.requisitos_aplicables(
                    None,
                    NS(
                        id_solicitante=1
                    ),
                    [r],
                    [],
                    [],
                ),
                [r],
            )

    def test_operadores_y_condiciones_invalidas(self):
        for cambios in (
            {
                "operador": "contiene"
            },
            {
                "valor": True
            },
            {
                "clave": "ajena"
            },
            {
                "script": "x"
            },
        ):
            with self.subTest(
                cambios=cambios
            ):
                with self.assertRaises(
                    svc.SeguimientoError
                ):
                    reglas.validar_condicion(
                        {
                            **self.r.condicion,
                            **cambios,
                        },
                        [self.campo],
                    )

        self.assertFalse(
            reglas.igualdad_simple(
                False,
                0,
            )
        )

        self.assertFalse(
            reglas.igualdad_simple(
                "1",
                1,
            )
        )


class PagoTest(unittest.TestCase):

    def respuesta(
        self,
        **cambios,
    ):
        datos = dict(
            encontrada=True,
            numero_factura="F-1",
            codigo="COD",
            documento_identidad="1234567",
            monto=Decimal("10.00"),
            moneda="BOB",
            estado_factura="pagada",
            utilizada=False,
        )

        datos.update(cambios)

        return PagoApiRespuesta(
            **datos
        )

    def test_api_debe_coincidir_en_todos_los_hechos(self):
        esperado = dict(
            numero_factura_esperado="F-1",
            codigo_esperado="COD",
            documento_esperado="1234567",
            monto_esperado=Decimal("10.00"),
            moneda_esperada="BOB",
        )

        self.assertTrue(
            pago._evaluar_respuesta_api(
                respuesta=self.respuesta(),
                **esperado,
            )[0]
        )

        fallos = [
            dict(
                encontrada=False
            ),
            dict(
                documento_identidad="otro"
            ),
            dict(
                numero_factura="otra"
            ),
            dict(
                codigo="otro"
            ),
            dict(
                monto=Decimal("11")
            ),
            dict(
                moneda="USD"
            ),
            dict(
                estado_factura="pendiente"
            ),
            dict(
                utilizada=True
            ),
        ]

        for fallo in fallos:
            with self.subTest(
                fallo=fallo
            ):
                self.assertFalse(
                    pago._evaluar_respuesta_api(
                        respuesta=self.respuesta(
                            **fallo
                        ),
                        **esperado,
                    )[0]
                )


class PagoServicioTest(unittest.TestCase):

    def setUp(self):
        self.db = Mock()

        self.r = requisito(
            es_economico=True,
            numero_factura="F-1",
            codigo_concepto_externo="COD",
            monto_economico=Decimal("10"),
            moneda="BOB",
        )

        self.s = NS(
            id_solicitud=1,
            estado="en_proceso",
        )

        self.stack = ExitStack()
        self.addCleanup(
            self.stack.close
        )

        self.stack.enter_context(
            patch.object(
                pago.seguimiento_repo,
                "bloquear_solicitud",
                return_value=self.s,
            )
        )

        self.stack.enter_context(
            patch.object(
                pago.solicitud_administrativa_repository,
                "obtener_solicitud_administrativa_por_id",
                return_value=self.s,
            )
        )

        self.stack.enter_context(
            patch.object(
                pago.solicitud_administrativa_repository,
                "obtener_requisito_solicitud_por_id",
                return_value=self.r,
            )
        )

        self.exito = self.stack.enter_context(
            patch.object(
                pago.pago_verificacion_repository,
                "obtener_verificacion_exitosa_por_factura",
                return_value=None,
            )
        )

        self.stack.enter_context(
            patch.object(
                pago,
                "obtener_documento_pago",
                return_value="1234567",
            )
        )

        self.api = self.stack.enter_context(
            patch.object(
                pago,
                "_consultar_api_pago",
                return_value=PagoApiRespuesta(
                    encontrada=True,
                    numero_factura="F-1",
                    codigo="COD",
                    documento_identidad="1234567",
                    monto=Decimal("10"),
                    moneda="BOB",
                    estado_factura="pagada",
                    utilizada=False,
                ),
            )
        )

        self.historial = self.stack.enter_context(
            patch.object(
                pago.seguimiento_repo,
                "registrar_historial",
            )
        )

        self.stack.enter_context(
            patch.object(
                pago,
                "registrar_accion_simple",
            )
        )

        def registrar(
            db,
            **datos,
        ):
            valores = dict(
                id_verificacion_pago=1,
                codigo_concepto_reportado=None,
                estado_factura_reportado=None,
                monto_reportado=None,
                moneda_reportada=None,
                fecha_verificacion=datetime.now(
                    timezone.utc
                ),
            )

            return NS(
                **(
                    valores
                    | datos
                )
            )

        self.stack.enter_context(
            patch.object(
                pago.pago_verificacion_repository,
                "crear_verificacion_pago",
                side_effect=registrar,
            )
        )

        def actualizar(
            db,
            requisito,
            **datos,
        ):
            for campo, valor in datos.items():
                setattr(
                    requisito,
                    campo,
                    valor,
                )

            return requisito

        self.stack.enter_context(
            patch.object(
                pago.solicitud_administrativa_repository,
                "actualizar_verificacion_requisito",
                side_effect=actualizar,
            )
        )

    def verificar(self):
        return pago.verificar_pago_requisito(
            self.db,
            id_solicitud=1,
            id_solicitud_requisito=1,
            id_usuario_verificador=8,
        )

    def test_verificacion_valida(self):
        resultado = self.verificar()

        self.assertEqual(
            self.r.estado_verificacion,
            "cumple",
        )

        self.assertEqual(
            resultado.estado,
            "verificado",
        )

    def test_factura_invalida_no_acredita(self):
        self.api.return_value = (
            self.api.return_value.model_copy(
                update={
                    "monto": Decimal("20")
                }
            )
        )

        resultado = self.verificar()

        self.assertEqual(
            resultado.estado,
            "no_verificado",
        )

        self.assertEqual(
            self.r.estado_verificacion,
            "no_cumple",
        )

    def test_timeout_deja_pendiente(self):
        self.r.estado_verificacion = (
            "no_cumple"
        )

        self.api.side_effect = TimeoutError()

        resultado = self.verificar()

        self.assertEqual(
            resultado.estado,
            "error",
        )

        self.assertEqual(
            self.r.estado_verificacion,
            "pendiente",
        )

    def test_pago_puede_verificarse_aunque_presentacion_fisica_siga_pendiente(self):
        self.r.requiere_presentacion_fisica = True
        self.r.presentado = False

        resultado = self.verificar()

        self.assertEqual(
            resultado.estado,
            "verificado",
        )

        self.assertEqual(
            self.r.estado_verificacion,
            "cumple",
        )

        self.assertFalse(
            self.r.presentado,
        )

        self.api.assert_called_once()


class EnvioSolicitudTest(unittest.TestCase):

    def test_envio_genera_snapshot_actual_sin_etapas(self):
        db = Mock()

        solicitud = NS(
            id_solicitud=1,
            id_solicitante=7,
            id_tramite=2,
            estado="borrador",
            nombre_contacto="Daniel",
            telefono_contacto="77777777",
            correo_contacto="daniel@example.com",
            nombre_tramite_snapshot=None,
            tipo_finalizacion=None,
            tipo_intervencion="ninguna",
        )

        tramite = NS(
            nombre="Trámite confirmado",
            tipo_finalizacion="resultado_registrado",
            tipo_intervencion="conformidad",
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

            marcar = stack.enter_context(
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

            historial = stack.enter_context(
                patch.object(
                    envio.seguimiento_repo,
                    "registrar_historial",
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
            "Trámite confirmado",
        )

        self.assertEqual(
            solicitud.tipo_finalizacion,
            "resultado_registrado",
        )

        self.assertEqual(
            solicitud.tipo_intervencion,
            "conformidad",
        )

        marcar.assert_called_once()
        historial.assert_called_once()
        db.commit.assert_called_once()

    def test_envio_exige_datos_basicos_actuales(self):
        db = Mock()

        solicitud = NS(
            id_solicitud=1,
            id_solicitante=7,
            id_tramite=2,
            estado="borrador",
            nombre_contacto=None,
            telefono_contacto=None,
            correo_contacto=None,
        )

        with (
            patch.object(
                envio,
                "_obtener_solicitud_del_usuario",
                return_value=solicitud,
            ),
            patch.object(
                envio,
                "_obtener_tramite_habilitado",
                return_value=NS(),
            ),
            patch.object(
                envio,
                "_obtener_perfil_minimo",
                return_value={
                    "carrera_programa": None,
                    "documento_identidad": None,
                },
            ),
        ):
            with self.assertRaises(
                envio.CamposObligatoriosFaltantesError
            ):
                envio.enviar_solicitud(
                    db,
                    id_solicitud=1,
                    id_solicitante=7,
                )

        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
