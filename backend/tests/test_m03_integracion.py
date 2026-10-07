"""Integración del contrato HTTP con almacenamiento simulado: nunca ejecuta SQL."""
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


@event.listens_for(Engine, 'do_connect')
def prohibir_conexion(*args):
    raise AssertionError('SQL prohibido en estas pruebas.')


from mock_pago_api import main as mock_api
from app.services.gestion_seguimiento import pago_api_client as cliente
from app.services.gestion_seguimiento import pago_verificacion_service as pago
from app.services.gestion_seguimiento import seguimiento_service as seguimiento
from app.services.gestion_seguimiento import datos_pago_service as identidad
from app.services.gestion_seguimiento import solicitud_service as envio
from app.schemas.gestion_seguimiento.pago_verificacion import PagoApiValidarRequest
from app.schemas.gestion_seguimiento.solicitud import SolicitudEnviarRequest


class ContratoPagoTest(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('sqlite3.connect', side_effect=AssertionError('SQLite prohibido')))
        self.stack.enter_context(patch.dict(os.environ, {'MOCK_PAGO_API_TOKEN': ''}))
        self.inicio = self.stack.enter_context(patch.object(mock_api, 'inicializar_base_datos'))
        self.http = self.stack.enter_context(TestClient(mock_api.app))

        def post(url, *, json, headers, timeout):
            respuesta = self.http.post('/api/v1/facturas/validar', json=json)
            return NS(ok=respuesta.is_success, status_code=respuesta.status_code, json=respuesta.json)
        self.transporte = self.stack.enter_context(patch.object(cliente.requests, 'post', side_effect=post))

    def consultar(self, factura, **cambios):
        return cliente.validar_factura(PagoApiValidarRequest(**{
            'codigo': 'MOCK-CERT-CONCLUSION-001', 'documento_identidad': '1234567',
            'numero_factura': factura, **cambios}))

    def evaluar(self, respuesta):
        return pago._evaluar_respuesta_api(respuesta=respuesta,
            numero_factura_esperado=respuesta.numero_factura, codigo_esperado='MOCK-CERT-CONCLUSION-001',
            documento_esperado='1234567', monto_esperado=Decimal('55.00'), moneda_esperada='BOB')[0]

    def test_inicio_health_y_factura_valida_sin_consumo(self):
        self.inicio.assert_called_once()
        self.assertEqual(self.http.get('/health').json(), {'status': 'ok'})
        a = self.consultar('FAC-PRUEBA-VALIDA')
        b = self.consultar('FAC-PRUEBA-VALIDA')
        self.assertTrue(self.evaluar(a))
        self.assertEqual(a, b)
        self.assertFalse(a.utilizada)
        enviado = self.transporte.call_args.kwargs['json']
        self.assertEqual(enviado['documento_identidad'], '1234567')
        self.assertEqual(enviado['codigo'], 'MOCK-CERT-CONCLUSION-001')

    def test_siete_discrepancias_no_acreditan(self):
        for caso in ('INEXISTENTE', 'CI', 'CODIGO', 'MONTO', 'MONEDA', 'PENDIENTE', 'UTILIZADA'):
            with self.subTest(caso=caso):
                self.assertFalse(self.evaluar(self.consultar('FAC-PRUEBA-' + caso)))

    def test_503_timeout_y_conexion_son_tecnicos(self):
        with self.assertRaises(cliente.PagoApiConexionError): self.consultar('FAC-PRUEBA-ERROR')
        for error in (requests.Timeout(), requests.ConnectionError()):
            self.transporte.side_effect = error
            with self.assertRaises(cliente.PagoApiConexionError): self.consultar('FAC-PRUEBA-VALIDA')

    def test_respuesta_sin_ci_no_se_acredita_por_suposion(self):
        self.transporte.side_effect = None
        self.transporte.return_value = NS(ok=True, json=lambda: {
            'encontrada': True, 'numero_factura': 'F-1', 'utilizada': False})
        with self.assertRaises(cliente.PagoApiRespuestaInvalidaError): self.consultar('F-1')

    def test_ci_obligatoria_y_token_mock(self):
        self.assertEqual(self.http.post('/api/v1/facturas/validar', json={
            'codigo': 'COD', 'numero_factura': 'F-1'}).status_code, 422)
        with patch.dict(os.environ, {'MOCK_PAGO_API_TOKEN': 'solo-prueba'}):
            self.assertEqual(self.http.post('/api/v1/facturas/validar', json={
                'codigo': 'COD', 'numero_factura': 'F-1', 'documento_identidad': '1234567'}).status_code, 401)


class IdentidadPagoTest(unittest.TestCase):
    def test_snapshot_prevalece_y_perfil_es_fallback(self):
        db = Mock(); s = NS(id_solicitud=1, id_solicitante=7)
        with patch.object(identidad.solicitud_repository, 'listar_datos_solicitud', return_value=[
            NS(clave_snapshot='documento_identidad', valor='1234567', campo=None)
        ]) as datos, patch.object(identidad.seguimiento_repository, 'obtener_perfil',
                                  return_value=NS(documento_identidad='7654321')) as perfil:
            self.assertEqual(identidad.obtener_documento_pago(db, s), '1234567')
            perfil.assert_not_called()
            datos.return_value = []
            self.assertEqual(identidad.obtener_documento_pago(db, s), '7654321')
            perfil.return_value = None
            self.assertIsNone(identidad.obtener_documento_pago(db, s))


class DeclaracionFisicaTest(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.r = NS(id_solicitud_requisito=1, nombre='Documento', requiere_presentacion_fisica=True,
                    presentado=False, estado_verificacion='pendiente', id_solicitud_etapa=None)
        self.s = NS(id_solicitud=1, id_solicitante=7, estado='pendiente_recepcion',
                    requisitos=[self.r], id_etapa_actual=None)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(seguimiento.repo, 'bloquear_solicitud', return_value=self.s))
        self.stack.enter_context(patch.object(seguimiento.repo, 'obtener_solicitud_completa', return_value=self.s))
        self.historial = self.stack.enter_context(patch.object(seguimiento.repo, 'listar_historial', return_value=[]))
        self.evento = self.stack.enter_context(patch.object(seguimiento, 'evento'))

    def test_declaracion_no_es_recepcion_y_repeticion_no_duplica(self):
        seguimiento.declarar_entrega_fisica(self.db, 1, 1, 7)
        self.assertFalse(self.r.presentado)
        self.assertEqual(self.r.estado_verificacion, 'pendiente')
        self.historial.return_value = [NS(evento='entrega_fisica_declarada', id_solicitud_requisito=1)]
        seguimiento.declarar_entrega_fisica(self.db, 1, 1, 7)
        self.evento.assert_called_once()

    def test_otro_propietario_estado_cerrado_y_etapa_futura_rechazados(self):
        with self.assertRaises(seguimiento.SeguimientoError): seguimiento.declarar_entrega_fisica(self.db, 1, 1, 8)
        self.s.estado = 'finalizada'
        with self.assertRaises(seguimiento.SeguimientoError): seguimiento.declarar_entrega_fisica(self.db, 1, 1, 7)
        self.s.estado = 'en_proceso'; self.s.id_etapa_actual = 10; self.r.id_solicitud_etapa = 20
        with self.assertRaises(seguimiento.SeguimientoError): seguimiento.declarar_entrega_fisica(self.db, 1, 1, 7)
        self.evento.assert_not_called()


class EnvioCombinadoTest(unittest.TestCase):
    def enviar(self, *, economico, fisico, posterior=False, declara=False, factura=False, ci='1234567'):
        db = Mock()
        s = NS(id_solicitud=1, id_solicitante=7, id_tramite=1, estado='borrador')
        r = NS(id_requisito=4, id_etapa=10 if posterior else None, nombre='Requisito',
               descripcion=None, obligatorio=True, orden=1, condicion=None,
               requiere_presentacion_fisica=fisico, configuraciones_economicas=[1] if economico else [])
        copia = NS(id_solicitud_requisito=30, presentado=False, estado_verificacion='pendiente')
        config = NS(id_requisito_economico=1, concepto='Pago', monto=Decimal('55'), moneda='BOB',
                    gestion=2026, codigo_concepto_externo='CONFIGURADO', activo=True)
        with ExitStack() as stack:
            for nombre, valor in [('_obtener_solicitud_del_usuario', s),
                ('_obtener_tramite_habilitado', NS(nombre='Trámite', tipo_finalizacion='entrega')),
                ('validar_flujo_envio', []), ('requisitos_aplicables', [r]),
                ('obtener_documento_pago', ci), ('_obtener_respuesta_completa', s)]:
                stack.enter_context(patch.object(envio, nombre, return_value=valor))
            for nombre, valor in [('listar_campos_tramite', []), ('listar_requisitos_tramite', [r]),
                                   ('obtener_configuracion_economica_por_gestion', config)]:
                stack.enter_context(patch.object(envio.tramite_repository, nombre, return_value=valor))
            for nombre, valor in [('listar_datos_solicitud', []), ('contar_requisitos_solicitud', 0)]:
                stack.enter_context(patch.object(envio.solicitud_repository, nombre, return_value=valor))
            crear = stack.enter_context(patch.object(envio.solicitud_repository, 'crear_requisito_solicitud', return_value=copia))
            stack.enter_context(patch.object(envio.solicitud_repository, 'marcar_solicitud_enviada'))
            stack.enter_context(patch.object(envio, 'registrar_accion_simple'))
            historia = stack.enter_context(patch.object(envio.seguimiento_repo, 'registrar_historial'))
            envio.enviar_solicitud(db, id_solicitud=1, id_solicitante=7, datos=SolicitudEnviarRequest(
                facturas=[{'id_requisito': 4, 'numero_factura': 'F-1'}] if factura else [],
                requisitos_fisicos_declarados=[4] if declara else []))
            return db, copia, crear.call_args.kwargs, [c.args[3] for c in historia.call_args_list]

    def test_cuatro_combinaciones_y_declaracion_sin_acreditacion(self):
        for economico, fisico in [(True, True), (True, False), (False, True), (False, False)]:
            with self.subTest(economico=economico, fisico=fisico):
                db, r, datos, eventos = self.enviar(economico=economico, fisico=fisico,
                                                  factura=economico, declara=fisico)
                db.commit.assert_called_once()
                self.assertEqual(datos['numero_factura'], 'F-1' if economico else None)
                self.assertEqual(datos['codigo_concepto_externo'], 'CONFIGURADO' if economico else None)
                self.assertEqual('entrega_fisica_declarada' in eventos, fisico)
                self.assertFalse(r.presentado)
                self.assertEqual(r.estado_verificacion, 'pendiente')

    def test_inicial_obligatorio_sin_factura_o_ci_no_envia(self):
        with self.assertRaises(envio.FacturaSolicitudInvalidaError):
            self.enviar(economico=True, fisico=False)
        with self.assertRaises(envio.FacturaSolicitudInvalidaError):
            self.enviar(economico=True, fisico=False, factura=True, ci=None)

    def test_no_se_declaran_requisitos_no_fisicos_o_futuros(self):
        for fisico, posterior in [(False, False), (True, True)]:
            with self.subTest(fisico=fisico, posterior=posterior), self.assertRaises(envio.FacturaSolicitudInvalidaError):
                self.enviar(economico=False, fisico=fisico, posterior=posterior, declara=True)


if __name__ == '__main__':
    unittest.main()
