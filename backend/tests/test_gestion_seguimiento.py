"""Reglas M03 sin PostgreSQL ni HTTP: unittest de la biblioteca estándar.

Desde backend: PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_gestion_seguimiento.py -v
"""
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from sqlalchemy import event
from sqlalchemy.engine import Engine

# Protección incluso si una futura edición intentara abrir una conexión real.
@event.listens_for(Engine, 'do_connect')
def prohibir_conexion(*args):
    raise AssertionError('Estas pruebas no pueden conectar a una base de datos.')

import app.models
from app.models.gestion_seguimiento import SolicitudEtapa, SolicitudResultado, SolicitudEntrega, SolicitudObservacion
from app.services.gestion_seguimiento import seguimiento_service as svc
from app.services.gestion_seguimiento import solicitud_service as envio
from app.services.gestion_seguimiento import configuracion_flujo_service as reglas
from app.services.gestion_seguimiento import pago_verificacion_service as pago
from app.schemas.gestion_seguimiento.seguimiento import (
    ResultadoRegistrarRequest, EntregaRegistrarRequest, ObservacionCrearRequest,
)
from app.schemas.gestion_seguimiento.solicitud import SolicitudEnviarRequest
from app.schemas.gestion_seguimiento.pago_verificacion import PagoApiRespuesta


def requisito(**cambios):
    datos = dict(id_solicitud_requisito=1, id_solicitud=1, nombre='Requisito', obligatorio=True,
                 id_solicitud_etapa=None, requiere_presentacion_fisica=False, presentado=False,
                 estado_verificacion='pendiente', es_economico=False, numero_factura=None)
    datos.update(cambios)
    return NS(**datos)


def etapa(id=10, orden=1, **cambios):
    datos = dict(id_solicitud_etapa=id, id_solicitud=1, id_etapa_origen=id,
                 nombre=f'Etapa {orden}', orden=orden, estado='pendiente', visible_solicitante=False,
                 fecha_inicio=None, fecha_finalizacion=None, id_usuario_inicio=None, id_usuario_finalizacion=None)
    datos.update(cambios)
    return NS(**datos)


class FlujoTest(unittest.TestCase):
    def setUp(self):
        self.s = NS(id_solicitud=1, id_solicitante=7, estado='en_revision', requisitos=[],
                    id_etapa_actual=None, tipo_finalizacion='entrega')
        self.etapas = [etapa(), etapa(20, 2)]
        self.observaciones = []
        self.pagos = []
        self.registros = []
        self.db = Mock()
        self.db.add.side_effect = self.registros.append
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for nombre, funcion in {
            'bloquear_solicitud': lambda *_: self.s,
            'obtener_solicitud_completa': lambda *_: self.s,
            'listar_etapas': lambda *_: self.etapas,
            'listar_observaciones': lambda *_: self.observaciones,
            'listar_pagos': lambda *_: self.pagos,
            'obtener_resultado': lambda *_: next((r for r in self.registros if isinstance(r, SolicitudResultado)), None),
            'obtener_entrega': lambda *_: next((r for r in self.registros if isinstance(r, SolicitudEntrega)), None),
        }.items():
            self.stack.enter_context(patch.object(svc.repo, nombre, side_effect=funcion))
        self.stack.enter_context(patch.object(svc, 'obtener_documento_pago', return_value='1234567'))
        self.evento = self.stack.enter_context(patch.object(svc, 'evento'))

    def test_etapas_lineales_y_peticion_repetida_no_salta_etapa(self):
        svc.iniciar_procesamiento(self.db, 1, 8)
        self.assertEqual(self.s.id_etapa_actual, 10)
        svc.avanzar_etapa(self.db, 1, 8, 10)
        self.assertEqual(self.s.id_etapa_actual, 20)
        with self.assertRaises(svc.SeguimientoError): svc.avanzar_etapa(self.db, 1, 8, 10)
        self.assertEqual(self.etapas[1].estado, 'en_curso')
        svc.avanzar_etapa(self.db, 1, 8, 20)
        self.assertEqual(self.s.id_etapa_actual, 20)
        self.assertEqual(self.s.estado, 'en_proceso')

    def test_requisito_inicial_bloquea_inicio(self):
        self.s.requisitos = [requisito()]
        with self.assertRaises(svc.SeguimientoError): svc.iniciar_procesamiento(self.db, 1, 8)
        self.assertEqual(self.s.estado, 'en_revision')
        self.db.commit.assert_not_called()

    def test_requisito_opcional_no_bloquea(self):
        self.s.requisitos = [requisito(obligatorio=False)]
        svc.iniciar_procesamiento(self.db, 1, 8)
        self.assertEqual(self.s.estado, 'en_proceso')

    def test_pago_posterior_no_bloquea_inicio_pero_si_su_etapa(self):
        r = requisito(id_solicitud_etapa=20, es_economico=True)
        self.s.requisitos = [r]
        svc.iniciar_procesamiento(self.db, 1, 8)
        with self.assertRaises(svc.SeguimientoError): svc.registrar_factura(self.db, 1, 1, 7, 'F-1')
        svc.avanzar_etapa(self.db, 1, 8, 10)
        svc.registrar_factura(self.db, 1, 1, 7, 'F-1')
        with self.assertRaises(svc.SeguimientoError): svc.avanzar_etapa(self.db, 1, 8, 20)
        r.estado_verificacion = 'cumple'
        svc.avanzar_etapa(self.db, 1, 8, 20)
        self.assertEqual(self.etapas[1].estado, 'completada')

    def test_presentacion_fisica_previa(self):
        r = requisito(requiere_presentacion_fisica=True, estado_verificacion='cumple')
        self.s.requisitos = [r]
        with self.assertRaises(svc.SeguimientoError): svc.iniciar_procesamiento(self.db, 1, 8)
        svc.registrar_presentacion(self.db, 1, 1, 8)
        self.assertTrue(r.presentado)
        self.assertEqual(r.id_usuario_presentacion, 8)
        svc.iniciar_procesamiento(self.db, 1, 8)

    def test_observacion_no_mueve_etapa_y_bloquea_hasta_resolucion(self):
        svc.iniciar_procesamiento(self.db, 1, 8)
        svc.crear_observacion(self.db, 1, 8, ObservacionCrearRequest(detalle='Falta original', correccion_requerida='Presentar original'))
        o = next(r for r in self.registros if isinstance(r, SolicitudObservacion))
        o.id_observacion = 5
        self.observaciones.append(o)
        self.assertEqual(self.s.id_etapa_actual, 10)
        self.assertEqual(self.s.estado, 'en_proceso')
        with self.assertRaises(svc.SeguimientoError): svc.avanzar_etapa(self.db, 1, 8, 10)
        svc.resolver_observacion(self.db, 1, 5, 8)
        self.assertEqual(self.s.id_etapa_actual, 10)
        svc.avanzar_etapa(self.db, 1, 8, 10)
        self.assertEqual(self.s.id_etapa_actual, 20)

    def test_observacion_bloquea_inicio_y_finalizacion(self):
        self.observaciones.append(NS(estado='pendiente'))
        with self.assertRaises(svc.SeguimientoError): svc.iniciar_procesamiento(self.db, 1, 8)
        self.s.estado='en_proceso'; self.etapas=[]
        with self.assertRaises(svc.SeguimientoError): svc.registrar_resultado(self.db, 1, 8, ResultadoRegistrarRequest())

    def test_rechazo_conserva_etapa_sin_completarla(self):
        svc.iniciar_procesamiento(self.db, 1, 8)
        svc.rechazar(self.db, 1, 8, 'No corresponde')
        self.assertEqual(self.s.estado, 'rechazada')
        self.assertEqual(self.etapas[0].estado, 'en_curso')
        with self.assertRaises(svc.SeguimientoError): svc.avanzar_etapa(self.db, 1, 8, 10)

    def test_cancelar_sin_factura_antes_de_recepcion(self):
        for estado in ('borrador', 'pendiente_recepcion'):
            with self.subTest(estado=estado):
                self.s.estado=estado
                svc.cancelar(self.db, 1, 7, 'Trámite incorrecto')
                self.assertEqual(self.s.estado, 'cancelada')
        self.s.estado='en_revision'
        with self.assertRaises(svc.SeguimientoError): svc.cancelar(self.db, 1, 7, 'Motivo')

    def test_cancelacion_bloqueada_por_factura_y_por_pago(self):
        self.s.estado='pendiente_recepcion'; self.s.requisitos=[requisito(numero_factura='F-1')]
        with self.assertRaises(svc.SeguimientoError): svc.cancelar(self.db, 1, 7, 'Motivo')
        self.s.requisitos=[]; self.pagos=[NS(estado='verificado')]
        with self.assertRaises(svc.SeguimientoError): svc.cancelar(self.db, 1, 7, 'Motivo')

    def test_propietario_no_puede_cancelar_otra_solicitud(self):
        self.s.estado='borrador'
        with self.assertRaises(svc.SeguimientoError) as e: svc.cancelar(self.db, 1, 99, 'Motivo')
        self.assertEqual(e.exception.status_code, 404)

    def test_requisito_ajeno_y_observacion_de_etapa_ajena(self):
        with self.assertRaises(svc.SeguimientoError): svc.registrar_presentacion(self.db, 1, 999, 8)
        with self.assertRaises(svc.SeguimientoError): svc.crear_observacion(self.db, 1, 8, ObservacionCrearRequest(id_solicitud_etapa=999, detalle='Detalle', correccion_requerida='Corregir'))

    def test_finalizacion_entrega_y_duplicados(self):
        self.s.estado='en_proceso'; self.etapas=[]
        svc.registrar_resultado(self.db, 1, 8, ResultadoRegistrarRequest(detalle='Disponible'))
        self.assertEqual(self.s.estado, 'lista_para_entrega')
        with self.assertRaises(svc.SeguimientoError): svc.registrar_resultado(self.db, 1, 8, ResultadoRegistrarRequest())
        svc.registrar_entrega(self.db, 1, 8, EntregaRegistrarRequest(receptor='tercero', nombre_receptor='Persona autorizada'))
        self.assertEqual(self.s.estado, 'finalizada')
        with self.assertRaises(svc.SeguimientoError): svc.registrar_entrega(self.db, 1, 8, EntregaRegistrarRequest(receptor='titular'))
        self.assertEqual(sum(isinstance(r, SolicitudEntrega) for r in self.registros),1)

    def test_modalidades_sin_entrega_y_no_sobrescribir_snapshot(self):
        self.s.estado='en_proceso'; self.etapas=[]; self.s.tipo_finalizacion='externo'
        with self.assertRaises(svc.SeguimientoError): svc.registrar_resultado(self.db, 1, 8, ResultadoRegistrarRequest(tipo_finalizacion='entrega'))
        svc.registrar_resultado(self.db, 1, 8, ResultadoRegistrarRequest())
        self.assertEqual(self.s.estado, 'finalizada')
        with self.assertRaises(svc.SeguimientoError): svc.registrar_entrega(self.db, 1, 8, EntregaRegistrarRequest(receptor='titular'))

    def test_legacy_sin_etapas_no_inventa_backfill(self):
        self.s.tipo_finalizacion=None; self.etapas=[]
        with self.assertRaises(svc.SeguimientoError): svc.iniciar_procesamiento(self.db, 1, 8)
        self.assertEqual(self.s.estado, 'en_revision')
        with self.assertRaises(svc.SeguimientoError): svc.registrar_resultado(self.db, 1, 8, ResultadoRegistrarRequest())
        svc.registrar_resultado(self.db, 1, 8, ResultadoRegistrarRequest(tipo_finalizacion='resultado_registrado'))
        self.assertEqual(self.s.estado, 'finalizada')
        self.assertFalse(any(isinstance(r, SolicitudEtapa) for r in self.registros))

    def test_requisito_cumplido_y_etapas_pendientes_bloquean_resultado(self):
        self.s.estado='en_proceso'
        with self.assertRaises(svc.SeguimientoError): svc.registrar_resultado(self.db,1,8,ResultadoRegistrarRequest())
        self.etapas=[]; self.s.requisitos=[requisito()]
        with self.assertRaises(svc.SeguimientoError): svc.registrar_resultado(self.db,1,8,ResultadoRegistrarRequest())

    def test_factura_acreditada_no_se_sustituye(self):
        self.s.requisitos=[requisito(es_economico=True, numero_factura='F-1', estado_verificacion='cumple')]
        svc.registrar_factura(self.db,1,1,7,'F-1')
        with self.assertRaises(svc.SeguimientoError): svc.registrar_factura(self.db,1,1,7,'F-2')
        self.evento.assert_not_called()

    def test_ningun_flush_deja_proceso_sin_referencia(self):
        def validar():
            if self.s.estado == 'en_proceso':
                self.assertIsNotNone(self.s.id_etapa_actual)
        self.db.flush.side_effect = validar
        self.evento.side_effect = lambda *a, **k: validar()
        svc.iniciar_procesamiento(self.db, 1, 8)
        svc.avanzar_etapa(self.db, 1, 8, 10)
        svc.avanzar_etapa(self.db, 1, 8, 20)
        self.assertEqual(self.s.id_etapa_actual, 20)
        self.assertEqual(self.etapas[-1].estado, 'completada')
        with self.assertRaises(svc.SeguimientoError): svc.avanzar_etapa(self.db, 1, 8, 20)
        svc.registrar_resultado(self.db, 1, 8, ResultadoRegistrarRequest())
        self.assertEqual(self.s.estado, 'lista_para_entrega')
        self.assertIsNone(self.s.id_etapa_actual)

    def test_revision_con_etapas_no_admite_resultado(self):
        with self.assertRaises(svc.SeguimientoError):
            svc.registrar_resultado(self.db, 1, 8, ResultadoRegistrarRequest())

    def test_evento_presentacion_referencia_snapshot(self):
        self.s.requisitos = [requisito(requiere_presentacion_fisica=True)]
        svc.registrar_presentacion(self.db, 1, 1, 8)
        self.assertEqual(self.evento.call_args.kwargs['requisito'], 1)
        self.assertIsNone(self.evento.call_args.kwargs['etapa'])


class CondicionesTest(unittest.TestCase):
    def setUp(self):
        self.campo=NS(id_campo=1, clave='motivo', activo=True, tipo_dato='seleccion', etiqueta='Motivo', configuracion={'opciones':['extravío','otro']})
        self.r=NS(condicion={'origen':'solicitud_dato','clave':'motivo','operador':'igual','valor':'extravío'})

    def test_condicion_filtra_snapshot_segun_datos(self):
        with patch.object(reglas.seguimiento_repository,'obtener_perfil',return_value=None):
            for valor,esperado in [('extravío',[self.r]),('otro',[])]:
                self.assertEqual(reglas.requisitos_aplicables(None, NS(id_solicitante=1),[self.r],[self.campo],[NS(id_campo=1,valor=valor)]),esperado)
            with self.assertRaises(svc.SeguimientoError): reglas.requisitos_aplicables(None,NS(id_solicitante=1),[self.r],[self.campo],[])

    def test_condicion_perfil(self):
        r=NS(condicion={'origen':'perfil_academico','campo':'carrera_programa','operador':'igual','valor':'Enfermería'})
        with patch.object(reglas.seguimiento_repository,'obtener_perfil',return_value=NS(carrera_programa='Enfermería')):
            self.assertEqual(reglas.requisitos_aplicables(None,NS(id_solicitante=1),[r],[],[]),[r])

    def test_tipo_invalido_y_operadores_no_autorizados(self):
        for cambios in [{'operador':'contiene'}, {'valor':True}, {'clave':'ajena'}, {'script':'x'}]:
            with self.subTest(cambios=cambios), self.assertRaises(svc.SeguimientoError): reglas.validar_condicion({**self.r.condicion,**cambios},[self.campo])
        self.assertFalse(reglas.igualdad_simple(False,0))
        self.assertFalse(reglas.igualdad_simple('1',1))


class PagoTest(unittest.TestCase):
    def respuesta(self,**cambios):
        return PagoApiRespuesta(**(dict(encontrada=True,numero_factura='F-1',codigo='COD',documento_identidad='1234567',monto=Decimal('10.00'),moneda='BOB',estado_factura='pagada',utilizada=False)|cambios))

    def test_api_debe_coincidir_en_todos_los_hechos(self):
        esperado=dict(numero_factura_esperado='F-1',codigo_esperado='COD',documento_esperado='1234567',monto_esperado=Decimal('10.00'),moneda_esperada='BOB')
        self.assertTrue(pago._evaluar_respuesta_api(respuesta=self.respuesta(),**esperado)[0])
        for fallo in [dict(encontrada=False),dict(documento_identidad='otro'),dict(numero_factura='otra'),dict(codigo='otro'),dict(monto=Decimal('11')),dict(moneda='USD'),dict(estado_factura='pendiente'),dict(utilizada=True)]:
            with self.subTest(fallo=fallo): self.assertFalse(pago._evaluar_respuesta_api(respuesta=self.respuesta(**fallo),**esperado)[0])

    def test_respuestas_invalidas_no_violan_columnas_de_intentos(self):
        r=self.respuesta(monto=Decimal('0'),codigo='',moneda='MONEDA',estado_factura='')
        self.assertTrue(all(v is None for v in pago._datos_reportados_almacenables(r).values()))
        r=self.respuesta(monto=Decimal('0.001'))
        self.assertIsNone(pago._datos_reportados_almacenables(r)['monto_reportado'])


class PagoServicioTest(unittest.TestCase):
    def setUp(self):
        self.db=Mock()
        self.r=requisito(es_economico=True,numero_factura='F-1',codigo_concepto_externo='COD',monto_economico=Decimal('10'),moneda='BOB')
        self.s=NS(id_solicitud=1,estado='en_revision',id_etapa_actual=None)
        self.stack=ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(pago.seguimiento_repo,'bloquear_solicitud',return_value=self.s))
        self.stack.enter_context(patch.object(pago.solicitud_administrativa_repository,'obtener_solicitud_administrativa_por_id',return_value=self.s))
        self.stack.enter_context(patch.object(pago.solicitud_administrativa_repository,'obtener_requisito_solicitud_por_id',return_value=self.r))
        self.exito=self.stack.enter_context(patch.object(pago.pago_verificacion_repository,'obtener_verificacion_exitosa_por_factura',return_value=None))
        self.documento=self.stack.enter_context(patch.object(pago,'obtener_documento_pago',return_value='1234567'))
        self.api=self.stack.enter_context(patch.object(pago,'_consultar_api_pago',return_value=PagoApiRespuesta(encontrada=True,numero_factura='F-1',codigo='COD',documento_identidad='1234567',monto=10,moneda='BOB',estado_factura='pagada',utilizada=False)))
        self.historial=self.stack.enter_context(patch.object(pago.seguimiento_repo,'registrar_historial'))
        self.stack.enter_context(patch.object(pago,'registrar_accion_simple'))
        def registrar(db, **datos):
            valores=dict(id_verificacion_pago=1,codigo_concepto_reportado=None,estado_factura_reportado=None,monto_reportado=None,moneda_reportada=None,fecha_verificacion=datetime.now(timezone.utc))
            return NS(**(valores | datos))
        self.stack.enter_context(patch.object(pago.pago_verificacion_repository,'crear_verificacion_pago',side_effect=registrar))
        def actualizar(db, r, **datos):
            for k,v in datos.items(): setattr(r,k,v)
            return r
        self.stack.enter_context(patch.object(pago.solicitud_administrativa_repository,'actualizar_verificacion_requisito',side_effect=actualizar))

    def verificar(self):
        return pago.verificar_pago_requisito(self.db,id_solicitud=1,id_solicitud_requisito=1,id_usuario_verificador=8)

    def test_verificacion_valida_y_repeticion_idempotente(self):
        resultado=self.verificar()
        self.assertEqual(self.r.estado_verificacion,'cumple')
        self.assertEqual(resultado.estado,'verificado')
        self.exito.return_value=resultado
        self.s.estado='finalizada'
        repetido=self.verificar()
        self.assertEqual(repetido.id_verificacion_pago,resultado.id_verificacion_pago)
        self.api.assert_called_once()
        self.historial.assert_called_once()
        self.db.commit.assert_called_once()

    def test_factura_invalida_no_acredita(self):
        self.api.return_value=self.api.return_value.model_copy(update={'monto':Decimal('20')})
        self.assertEqual(self.verificar().estado,'no_verificado')
        self.assertEqual(self.r.estado_verificacion,'no_cumple')

    def test_timeout_deja_pendiente_sin_acreditar(self):
        self.r.estado_verificacion='no_cumple'
        self.api.side_effect=TimeoutError()
        respuesta=self.verificar()
        self.assertEqual(respuesta.estado,'error')
        self.assertEqual(self.r.estado_verificacion,'pendiente')
        self.assertNotIn('permanece pendiente',respuesta.mensaje)
        self.historial.assert_called_once()

    def test_factura_ya_acredito_otro_requisito(self):
        self.exito.return_value=NS(id_solicitud_requisito=99)
        with self.assertRaises(pago.FacturaYaUtilizadaError): self.verificar()
        self.api.assert_not_called()

    def test_pago_exige_etapa_actual_y_presentacion(self):
        self.r.id_solicitud_etapa=20
        with self.assertRaises(svc.SeguimientoError): self.verificar()
        self.s.estado='en_proceso'; self.s.id_etapa_actual=20
        self.r.requiere_presentacion_fisica=True
        with self.assertRaises(svc.SeguimientoError): self.verificar()
        self.api.assert_not_called()

    def test_fallo_historial_revierte_transaccion(self):
        self.historial.side_effect=RuntimeError('fallo simulado')
        with self.assertRaises(RuntimeError): self.verificar()
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()


class EnvioTest(unittest.TestCase):
    def test_snapshot_pago_posterior_sin_factura_y_sin_inventar_requisitos(self):
        db=Mock(); s=NS(id_solicitud=1,id_solicitante=7,id_tramite=2,estado='borrador')
        plantilla=NS(id_etapa=10,id_unidad=None,nombre='Revisión',descripcion=None,orden=1,es_inicial=True,es_final=True,visible_solicitante=True)
        req=NS(id_requisito=4,nombre='Pago posterior',descripcion=None,obligatorio=True,orden=1,id_etapa=10,requiere_presentacion_fisica=False,condicion=None,configuraciones_economicas=[1])
        config=NS(id_requisito_economico=6,concepto='Concepto configurable',monto=Decimal('10'),moneda='BOB',gestion=2026,codigo_concepto_externo='CONFIGURADO',activo=True)
        capturados=[]
        def add(o):
            if isinstance(o,SolicitudEtapa):o.id_solicitud_etapa=55;capturados.append(o)
        def copiar(*args,**kw):
            r=NS(**kw);capturados.append(r);return r
        db.add.side_effect=add
        with ExitStack() as stack:
            for nombre,resultado in [('_obtener_solicitud_del_usuario',s),('_obtener_tramite_habilitado',NS(nombre='Trámite confirmado',tipo_finalizacion='entrega')),('validar_flujo_envio',[plantilla]),('_obtener_respuesta_completa',s)]:
                stack.enter_context(patch.object(envio,nombre,return_value=resultado))
            stack.enter_context(patch.object(envio,'registrar_accion_simple'))
            stack.enter_context(patch.object(envio.seguimiento_repo,'registrar_historial'))
            stack.enter_context(patch.object(envio.seguimiento_repo,'obtener_perfil',return_value=None))
            for nombre,resultado in [('listar_campos_tramite',[]),('listar_requisitos_tramite',[req]),('obtener_configuracion_economica_por_gestion',config)]:
                stack.enter_context(patch.object(envio.tramite_repository,nombre,return_value=resultado))
            for nombre,resultado in [('listar_datos_solicitud',[]),('contar_requisitos_solicitud',0)]:
                stack.enter_context(patch.object(envio.solicitud_repository,nombre,return_value=resultado))
            stack.enter_context(patch.object(envio.solicitud_repository,'crear_requisito_solicitud',side_effect=copiar))
            stack.enter_context(patch.object(envio.solicitud_repository,'marcar_solicitud_enviada'))
            envio.enviar_solicitud(db,id_solicitud=1,id_solicitante=7,datos=SolicitudEnviarRequest())
            self.assertEqual(capturados[1].id_solicitud_etapa,55)
            self.assertIsNone(capturados[1].numero_factura)
            self.assertEqual(s.tipo_finalizacion,'entrega')
            self.assertEqual(s.nombre_tramite_snapshot,'Trámite confirmado')
            req.nombre='Catálogo cambiado'; plantilla.nombre='Etapa cambiada'
            self.assertEqual(capturados[0].nombre,'Revisión')
            self.assertEqual(capturados[1].nombre,'Pago posterior')
            db.commit.assert_called_once()
            req.id_etapa=None
            with self.assertRaises(envio.FacturaSolicitudInvalidaError): envio.enviar_solicitud(db,id_solicitud=1,id_solicitante=7,datos=SolicitudEnviarRequest())
            db.rollback.assert_called()


if __name__ == '__main__':
    unittest.main()
