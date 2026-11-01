"""Analítica: contratos y consultas compiladas, sin ejecutar SQL ni proveedores."""
from contextlib import ExitStack
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
import socket

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.core.dependencies import obtener_usuario_activo
from app.db.session import get_db
from app.repositories import analitica_repository as repo
from app.schemas.analitica import FiltrosAnalitica
from app.services import analitica_service as service


AHORA = datetime(2026, 10, 14, 18, tzinfo=timezone.utc)


def agregados():
    return dict(tramites=[dict(id_tramite=2, nombre='Certificado')], recibidas=[],
                resumen=dict(concluidas=0, mediana=None, sin_fecha=0),
                concluidas=[], top=[], rag=[])


class Aisladas(TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Engine, 'connect', side_effect=AssertionError('SQL prohibido')))
        self.stack.enter_context(patch.object(socket.socket, 'connect', side_effect=AssertionError('Red prohibida')))


class PeriodosTests(Aisladas):
    def test_dias_calendario_y_zona(self):
        for periodo, dias in [('30_dias', 29), ('90_dias', 89)]:
            desde, hasta, grupo = service.resolver_periodo(periodo, AHORA)
            self.assertEqual((hasta.date() - desde.date()).days, dias)
            self.assertEqual(desde.hour, 0)
            self.assertEqual(hasta.hour, 14)
            self.assertEqual(grupo, 'week')

    def test_doce_meses_incluye_actual(self):
        desde, hasta, grupo = service.resolver_periodo('12_meses', AHORA)
        self.assertEqual(desde.date(), date(2025, 11, 1))
        self.assertEqual(len(list(service.periodos_serie(desde, hasta, grupo))), 12)

    def test_limite_utc_es_dia_anterior_en_la_paz(self):
        desde, hasta, _ = service.resolver_periodo('30_dias', datetime(2026, 1, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(hasta.date(), date(2025, 12, 31))
        self.assertEqual(desde.date(), date(2025, 12, 2))

    def test_semana_comienza_lunes(self):
        desde, hasta, grupo = service.resolver_periodo('90_dias', AHORA)
        puntos = list(service.periodos_serie(desde, hasta, grupo))
        self.assertTrue(all(p.weekday() == 0 for p in puntos))
        self.assertLessEqual(puntos[0], desde.date())
        self.assertLessEqual(puntos[-1], hasta.date())

    def test_bisiesto(self):
        desde, hasta, grupo = service.resolver_periodo('12_meses', datetime(2024, 2, 29, 12, tzinfo=timezone.utc))
        self.assertEqual(desde.date(), date(2023, 3, 1))
        self.assertEqual(len(list(service.periodos_serie(desde, hasta, grupo))), 12)

    def test_rechaza_fecha_ingenua_y_periodo_arbitrario(self):
        with self.assertRaises(ValueError):
            service.resolver_periodo('30_dias', datetime(2026, 10, 14))
        with self.assertRaises(ValueError):
            service.resolver_periodo('100_anos', AHORA)


class ServiceTests(Aisladas):
    def setUp(self):
        super().setUp()
        self.datos = agregados()
        self.consulta = self.stack.enter_context(patch.object(repo, 'consultar_agregados', return_value=self.datos))

    def obtener(self, id_tramite=None):
        return service.obtener_analitica(Mock(), FiltrosAnalitica(id_tramite=id_tramite), ahora=AHORA)

    def test_vacio_distingue_cero_y_mediana_no_disponible(self):
        r = self.obtener()
        self.assertEqual(r.indicadores.solicitudes_recibidas, 0)
        self.assertEqual(r.indicadores.solicitudes_concluidas, 0)
        self.assertEqual(r.indicadores.consultas_rag, 0)
        self.assertIsNone(r.indicadores.tiempo_mediano_dias)
        self.assertEqual(r.top_tramites, [])
        self.assertTrue(all(p.recibidas == p.concluidas == 0 for p in r.evolucion_solicitudes))

    def test_resumen_deriva_de_agregados_y_rellena_huecos(self):
        p = datetime(2026, 10, 12)
        self.datos.update(recibidas=[dict(periodo=p, cantidad=5)],
                          concluidas=[dict(periodo=p, cantidad=2)],
                          rag=[dict(periodo=p, cantidad=7)],
                          resumen=dict(concluidas=2, mediana=1.5, sin_fecha=0))
        r = self.obtener(2)
        self.assertEqual(r.indicadores.model_dump(), dict(solicitudes_recibidas=5,
            solicitudes_concluidas=2, tiempo_mediano_dias=1.5, consultas_rag=7))
        self.assertEqual(sum(p.recibidas for p in r.evolucion_solicitudes), 5)
        self.assertEqual(sum(p.consultas for p in r.evolucion_rag), 7)
        self.assertEqual(self.consulta.call_args.kwargs['id_tramite'], 2)

    def test_mediana_cero_es_valida(self):
        self.datos['resumen'] = dict(concluidas=1, mediana=0, sin_fecha=0)
        self.assertEqual(self.obtener().indicadores.tiempo_mediano_dias, 0)

    def test_fecha_final_desconocida_no_se_aproxima(self):
        self.datos['resumen'] = dict(concluidas=2, mediana=1.5, sin_fecha=1)
        r = self.obtener()
        self.assertIsNone(r.indicadores.solicitudes_concluidas)
        self.assertIsNone(r.indicadores.tiempo_mediano_dias)
        self.assertTrue(all(p.concluidas is None for p in r.evolucion_solicitudes))
        self.assertIn('fecha de conclusión fiable', r.limitaciones[-1])

    def test_id_inexistente(self):
        with self.assertRaises(service.TramiteAnaliticaNoEncontrado):
            self.obtener(999)

    def test_no_clasifica_rag(self):
        r = self.obtener()
        self.assertFalse(r.clasificacion_rag_disponible)
        self.assertNotIn('autenticadas', r.evolucion_rag[0].model_dump())


class ConsultasTests(Aisladas):
    def consultas(self, id_tramite=None):
        db = Mock()
        db.execute.return_value.mappings.return_value.all.return_value = []
        db.execute.return_value.mappings.return_value.one.return_value = dict(concluidas=0, mediana=None, sin_fecha=0)
        desde, hasta, grupo = service.resolver_periodo('30_dias', AHORA)
        repo.consultar_agregados(db, desde=desde, hasta=hasta, agrupacion=grupo,
                                zona=service.ZONA, id_tramite=id_tramite)
        self.assertEqual(db.execute.call_count, 6)
        db.commit.assert_not_called()
        db.add.assert_not_called()
        return [str(c.args[0].compile(dialect=postgresql.dialect(),
                    compile_kwargs={'literal_binds': True})) for c in db.execute.call_args_list]

    def test_recibidas_fecha_creacion_y_limites_semiabiertos(self):
        sql = self.consultas()[1]
        self.assertIn('solicitud.fecha_creacion >=', sql)
        self.assertIn('solicitud.fecha_creacion <', sql)
        self.assertNotIn('fecha_envio', sql)
        self.assertNotIn('historial', sql)
        self.assertIn("timezone('America/La_Paz'", sql)

    def test_conclusion_y_mediana_postgresql(self):
        sql = self.consultas()[2]

        self.assertIn(
            "percentile_cont(0.5) WITHIN GROUP",
            sql,
        )

        self.assertIn(
            "EXTRACT(epoch FROM",
            sql,
        )

        self.assertIn(
            "86400",
            sql,
        )

        self.assertIn(
            "FILTER (WHERE",
            sql,
        )

        self.assertIn(
            "solicitud_resultado.fecha_registro",
            sql,
        )

        self.assertIn(
            "solicitud_resultado.tipo_finalizacion = solicitud.tipo_finalizacion",
            sql,
        )

        self.assertIn(
            "solicitud.estado = 'finalizada'",
            sql,
        )

        self.assertIn(
            "solicitud.estado = 'lista_para_entrega'",
            sql,
        )

        self.assertIn(
            "solicitud.tipo_finalizacion = 'entrega'",
            sql,
        )

        self.assertNotIn(
            "solicitud_entrega",
            sql,
        )

        self.assertNotIn(
            "fecha_actualizacion",
            sql,
        )

        self.assertNotIn(
            "avg(",
            sql,
        )

    def test_top_cinco_orden_y_nombre_real(self):
        sql = self.consultas()[4]
        self.assertIn('tramite.nombre', sql)
        self.assertIn('ORDER BY count(solicitud.id_solicitud) DESC, tramite.id_tramite', sql)
        self.assertIn('LIMIT 5', sql)

    def test_rag_solo_user_y_sin_filtro_tramite(self):
        consultas = self.consultas(2)
        for indice in [1, 2, 3, 4]:
            self.assertIn('solicitud.id_tramite = 2', consultas[indice])
        self.assertIn("chat_message.role = 'user'", consultas[5])
        self.assertNotIn('id_tramite', consultas[5])
        self.assertNotIn('content', consultas[5])
        self.assertNotIn('chat_session', consultas[5])
        self.assertEqual(consultas[5], self.consultas()[5])


class ApiTests(Aisladas):
    def setUp(self):
        super().setUp()
        self.addCleanup(app.dependency_overrides.clear)
        app.dependency_overrides[get_db] = lambda: Mock()
        self.client = TestClient(app)
        self.mock_datos = self.stack.enter_context(patch.object(repo, 'consultar_agregados', return_value=agregados()))

    def rol(self, nombre, activo=True):
        app.dependency_overrides[obtener_usuario_activo] = lambda: SimpleNamespace(asignaciones_rol=[
            SimpleNamespace(activo=activo, fecha_revocacion=None,
                            rol=SimpleNamespace(nombre=nombre, activo=True))])

    def test_anonimo_no_accede(self):
        self.assertEqual(self.client.get('/api/admin/analitica').status_code, 401)
        self.mock_datos.assert_not_called()

    def test_solicitante_y_rol_revocado_no_acceden(self):
        for rol, activo in [('solicitante', True), ('administrador', False)]:
            self.rol(rol, activo)
            self.assertEqual(self.client.get('/api/admin/analitica').status_code, 403)
        self.mock_datos.assert_not_called()

    def test_roles_administrativos_y_contrato_sin_datos_personales(self):
        for rol in ['administrador', 'personal_administrativo']:
            self.rol(rol)
            r = self.client.get('/api/admin/analitica')
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(set(r.json()['indicadores']), {'solicitudes_recibidas',
                'solicitudes_concluidas', 'tiempo_mediano_dias', 'consultas_rag'})
            self.assertNotIn('correo', r.text)
            self.assertNotIn('content', r.text)

    def test_filtros_invalidos(self):
        self.rol('administrador')
        for query in ['periodo=100_anos', 'id_tramite=0', 'id_tramite=-1', 'id_tramite=abc']:
            self.assertEqual(self.client.get('/api/admin/analitica?' + query).status_code, 422)
        self.mock_datos.assert_not_called()

    def test_id_desconocido(self):
        self.rol('administrador')
        self.assertEqual(self.client.get('/api/admin/analitica?id_tramite=999').status_code, 404)

    def test_error_consulta_no_es_cero_ni_expone_detalles(self):
        self.rol('administrador')
        self.mock_datos.side_effect = SQLAlchemyError('detalle privado')
        r = self.client.get('/api/admin/analitica')
        self.assertEqual(r.status_code, 503)
        self.assertNotIn('detalle privado', r.text)
        self.assertNotIn('indicadores', r.json())
