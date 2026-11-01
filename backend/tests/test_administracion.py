"""Administración: pruebas sin SQL ni proveedores reales, usando unittest existente."""
from contextlib import ExitStack
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import socket
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine

import app.models
import app.models.usuario_identidad_externa
from app.core.dependencies import exigir_roles, exigir_administrador
from app.repositories import documento_repository, chunk_repository, usuario_repository
from app.schemas.documento import DocumentoCrearRequest, VersionCrearRequest, VigenciaDocumentoRequest
from app.schemas.gestion_seguimiento.tramite import TramiteActualizarRequest
from app.services.auth import role_service as roles, user_service as users
from app.services.gestion_seguimiento import tramite_service as tramites
from app.services.rag import documento_service as docs
from app.services.rag import ingest


class PruebasAisladas(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Engine, 'connect', side_effect=AssertionError('SQL prohibido')))
        self.stack.enter_context(patch.object(socket.socket, 'connect', side_effect=AssertionError('Red prohibida')))
        self.db = Mock()

    def mock(self, modulo, nombre, **kwargs):
        return self.stack.enter_context(patch.object(modulo, nombre, **kwargs))


class UsuariosTests(PruebasAisladas):
    def setUp(self):
        super().setUp()
        self.usuario = NS(id_usuario=7, estado='activo')
        self.mock(roles, 'usuario_tiene_rol', return_value=True)
        self.otros = self.mock(roles, 'contar_otros_administradores', return_value=0)

    def test_ultimo_administrador_protegido(self):
        with self.assertRaises(roles.UltimoAdministradorError):
            roles.proteger_ultimo_administrador(self.db, self.usuario)

    def test_otro_administrador_valido_permite_cambio(self):
        self.otros.return_value = 1
        roles.proteger_ultimo_administrador(self.db, self.usuario)

    def test_revocacion_serializa_antes_de_verificar_y_no_revoca_al_ultimo(self):
        llamadas = []
        self.mock(roles, 'bloquear_administracion', side_effect=lambda *_: llamadas.append('cerrojo'))
        self.mock(roles, 'obtener_usuario_por_id', side_effect=lambda *a, **kw: (llamadas.append('usuario'), self.usuario)[1])
        self.mock(roles, 'obtener_rol_por_id', return_value=NS(nombre='administrador'))
        self.mock(roles, 'obtener_asignacion', return_value=NS(activo=True, fecha_revocacion=None))
        revocar = self.mock(roles, 'revocar_asignacion')
        with self.assertRaises(roles.UltimoAdministradorError):
            roles.revocar_rol_usuario(self.db, id_usuario=7, id_rol=3, id_usuario_actor=7)
        self.assertEqual(llamadas, ['cerrojo', 'usuario'])
        revocar.assert_not_called()
        self.db.commit.assert_not_called()

    def test_no_asigna_rol_duplicado(self):
        self.mock(roles, 'bloquear_administracion')
        self.mock(roles, 'obtener_usuario_por_id', return_value=self.usuario)
        self.mock(roles, 'obtener_rol_por_id', return_value=NS(activo=True))
        self.mock(roles, 'obtener_asignacion', return_value=NS(activo=True, fecha_revocacion=None))
        crear = self.mock(roles, 'crear_asignacion_rol')
        with self.assertRaises(roles.RolYaAsignadoError):
            roles.asignar_rol_usuario(self.db, id_usuario=7, id_rol=3, id_usuario_actor=7)
        crear.assert_not_called()

    def test_estados_no_activos_no_pueden_quitar_al_ultimo_admin(self):
        self.mock(users, 'bloquear_administracion')
        self.mock(users, 'obtener_usuario_por_id', return_value=self.usuario)
        actualizar = self.mock(users, 'actualizar_estado_usuario')
        for estado in ('inactivo', 'bloqueado', 'pendiente_verificacion'):
            with self.subTest(estado=estado), self.assertRaises(users.EstadoUsuarioInvalidoError):
                users.cambiar_estado_usuario(self.db, id_usuario=7, nuevo_estado=estado, id_usuario_actor=7)
        actualizar.assert_not_called()

    def test_desactivar_revoca_sesiones_y_audita(self):
        self.otros.return_value = 1
        self.mock(users, 'bloquear_administracion')
        self.mock(users, 'obtener_usuario_por_id', return_value=self.usuario)
        self.mock(users, 'actualizar_estado_usuario')
        sesiones = self.mock(users, 'revocar_sesiones_usuario', return_value=2)
        auditoria = self.mock(users, 'registrar_accion_simple')
        self.mock(users, 'obtener_usuario_administracion', return_value=NS())
        users.cambiar_estado_usuario(self.db, id_usuario=7, nuevo_estado='inactivo', id_usuario_actor=8)
        sesiones.assert_called_once()
        self.assertEqual(auditoria.call_args.kwargs['accion'], 'cambiar_estado_usuario')
        self.db.commit.assert_called_once()

    def test_lista_serializa_correo_orm_como_texto(self):
        correo = NS(correo='persona@example.org', activo=True, es_principal=True)
        usuario = NS(id_usuario=7, nombres='Persona', apellidos='Prueba', estado='activo',
                     fecha_ultimo_acceso=None, fecha_creacion=datetime(2026, 1, 1),
                     correos=[correo], correo_principal=correo, asignaciones_rol=[])
        self.mock(users, 'listar_usuarios', return_value=([usuario], 1))
        lista = users.listar_usuarios_administracion(self.db)
        self.assertEqual(lista.items[0].correo_principal, 'persona@example.org')

    def test_filtro_rol_paginate_y_activo_en_servidor(self):
        self.db.scalar.return_value = 0
        self.db.scalars.return_value.unique.return_value.all.return_value = []
        usuario_repository.listar_usuarios(self.db, pagina=2, por_pagina=20, id_rol=3)
        sql = str(self.db.scalars.call_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
        self.assertIn('usuario_rol.id_rol = 3', sql)
        self.assertIn('fecha_revocacion IS NULL', sql)
        self.assertIn('OFFSET 20', sql)


class TramitesTests(PruebasAisladas):
    def test_desactivar_tambien_impide_publicacion_y_nuevas_solicitudes(self):
        tramite = NS(
            id_tramite=1,
            nombre="Trámite",
            descripcion=None,
            activo=True,
            publicado=True,
            permite_solicitudes=True,
            tipo_finalizacion="resultado_registrado",
            tipo_intervencion="ninguna",
        )

        self.mock(
            tramites,
            "_obtener_tramite_o_error",
            return_value=tramite,
        )

        actualizar = self.mock(
            tramites.repo,
            "actualizar_tramite",
        )

        self.mock(tramites, "_aplicar_extension")
        self.mock(tramites, "registrar_accion_simple")
        self.mock(
            tramites,
            "_respuesta_tramite",
            return_value=NS(),
        )

        tramites.actualizar_tramite_catalogo(
            self.db,
            id_tramite=1,
            datos=TramiteActualizarRequest(
                activo=False
            ),
            id_usuario_actor=7,
        )

        self.assertFalse(
            actualizar.call_args.kwargs["activo"]
        )
        self.assertFalse(
            actualizar.call_args.kwargs["publicado"]
        )
        self.assertFalse(
            actualizar.call_args.kwargs[
                "permite_solicitudes"
            ]
        )

    def test_estado_tramite_impide_combinaciones_invalidas(self):
        with self.assertRaises(
            tramites.ConfiguracionTramiteInvalidaError
        ):
            tramites._validar_estado_tramite(
                activo=False,
                publicado=True,
                permite_solicitudes=False,
            )

        with self.assertRaises(
            tramites.ConfiguracionTramiteInvalidaError
        ):
            tramites._validar_estado_tramite(
                activo=True,
                publicado=False,
                permite_solicitudes=True,
            )

        tramites._validar_estado_tramite(
            activo=True,
            publicado=True,
            permite_solicitudes=True,
        )

    def test_requisitos_ya_no_se_asocian_a_etapas(self):
        datos = Mock()
        datos.model_dump.return_value = {
            "id_etapa": 10
        }

        with self.assertRaises(
            tramites.ConfiguracionTramiteInvalidaError
        ):
            tramites._validar_extension_requisito(
                self.db,
                1,
                datos,
            )

    def test_intervencion_exige_finalizacion_por_resultado(self):
        tramite = NS(
            tipo_intervencion="ninguna",
            tipo_finalizacion="entrega",
        )

        datos = Mock()
        datos.model_dump.return_value = {
            "tipo_intervencion": "firma",
            "tipo_finalizacion": "entrega",
        }

        with self.assertRaises(
            tramites.ConfiguracionTramiteInvalidaError
        ):
            tramites._validar_intervencion(
                tramite,
                datos,
            )


class DocumentosTests(PruebasAisladas):
    def setUp(self):
        super().setUp()

        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.mock(
            docs,
            "DOCUMENTS_DIR",
            new=Path(self.temporal.name),
        )

        self.documento = NS(
            id_documento_institucional=1,
            id_version_actual=10,
            estado="activo",
        )

        self.version = NS(
            id_version_documento=10,
            id_documento_institucional=1,
            hash_archivo="hash",
            vigente_desde=date(2026, 1, 1),
            vigente_hasta=date(2026, 12, 31),
            fecha_version=datetime(2025, 1, 1),
            estado="activo",
        )

        self.mock(
            docs.repo,
            "obtener_documento",
            return_value=self.documento,
        )

        self.mock(
            docs.repo,
            "obtener_version",
            return_value=self.version,
        )

        self.mock(
            docs.repo,
            "guardar_cambios",
        )

        self.mock(
            docs.repo,
            "modo_version",
            return_value="normativo",
        )

        self.mock(
            docs,
            "detalle_documento",
            return_value=NS(),
        )

        self.mock(
            docs,
            "_fecha_actual_bd",
            return_value=date(2026, 1, 1),
        )

        self.cerrar = self.mock(
            docs,
            "_cerrar_version_anterior",
        )

        self.auditar = self.mock(
            docs,
            "registrar_accion_simple",
        )

        self.preparar = self.mock(
            docs,
            "preparar_chunks",
            return_value=(
                "hash",
                [{"contenido": "Texto"}],
            ),
        )

        self.chunks = self.mock(
            docs.repo,
            "guardar_chunks",
        )

        self.archivo = self.mock(
            docs.repo,
            "guardar_archivo_pdf",
        )

        self.actualizar = self.mock(
            docs.repo,
            "establecer_version_actual",
        )

    def test_vigencia_rechaza_fechas_invertidas(self):
        with self.assertRaises(ValidationError):
            VigenciaDocumentoRequest(
                vigente_desde="2026-05-10",
                vigente_hasta="2026-05-09",
            )

    def test_limites_vigencia_y_compatibilidad_historica(self):
        self.assertTrue(
            docs.version_vigente(
                self.version,
                date(2026, 1, 1),
            )
        )

        self.assertTrue(
            docs.version_vigente(
                self.version,
                date(2026, 12, 31),
            )
        )

        self.assertFalse(
            docs.version_vigente(
                self.version,
                date(2027, 1, 1),
            )
        )

        self.assertFalse(
            docs.version_vigente(
                self.version,
                date(2025, 12, 31),
            )
        )

        self.version.vigente_desde = None
        self.version.vigente_hasta = None

        self.assertTrue(
            docs.version_vigente(
                self.version,
                date(2026, 1, 1),
            )
        )

    def test_desactivar_no_borra_chunks_ni_cambia_version(self):
        docs.actualizar_documento(
            self.db,
            1,
            7,
            estado="inactivo",
        )

        self.assertEqual(
            self.documento.estado,
            "inactivo",
        )

        self.chunks.assert_not_called()
        self.actualizar.assert_not_called()
        self.preparar.assert_not_called()
        self.auditar.assert_called_once()

    def test_reingesta_reemplaza_solo_version_seleccionada(self):
        self.mock(
            docs,
            "_leer_pdf",
            return_value=b"contenido",
        )

        docs.actualizar_documento(
            self.db,
            1,
            7,
            id_version=10,
            reingestar=True,
        )

        self.chunks.assert_called_once_with(
            self.db,
            10,
            [{"contenido": "Texto"}],
            reemplazar=True,
        )

        self.actualizar.assert_not_called()
        self.db.commit.assert_called_once()

    def test_fallo_reingesta_no_toca_chunks_previos(self):
        self.mock(
            docs,
            "_leer_pdf",
            return_value=b"contenido",
        )

        self.preparar.side_effect = RuntimeError(
            "proveedor no disponible"
        )

        with self.assertRaises(
            docs.DocumentoError
        ):
            docs.actualizar_documento(
                self.db,
                1,
                7,
                id_version=10,
                reingestar=True,
            )

        self.chunks.assert_not_called()
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()

    def test_archivo_modificado_exige_nueva_version(self):
        self.mock(
            docs,
            "_leer_pdf",
            return_value=b"contenido",
        )

        self.preparar.return_value = (
            "hash-distinto",
            [],
        )

        with self.assertRaises(
            docs.DocumentoError
        ) as exc:
            docs.actualizar_documento(
                self.db,
                1,
                7,
                id_version=10,
                reingestar=True,
            )

        self.assertEqual(
            exc.exception.status_code,
            409,
        )

        self.chunks.assert_not_called()

    def test_fallo_persistencia_reingesta_revierte_transaccion(self):
        self.mock(
            docs,
            "_leer_pdf",
            return_value=b"contenido",
        )

        self.chunks.side_effect = RuntimeError(
            "error al persistir"
        )

        with self.assertRaises(
            docs.DocumentoError
        ):
            docs.actualizar_documento(
                self.db,
                1,
                7,
                id_version=10,
                reingestar=True,
            )

        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()
        self.actualizar.assert_not_called()

    def test_nueva_version_no_publica_si_ingesta_falla(self):
        path = Mock()

        self.mock(
            docs,
            "guardar_pdf",
            return_value=path,
        )

        self.preparar.side_effect = RuntimeError(
            "fallo de extracción"
        )

        crear = self.mock(
            docs.repo,
            "crear_version",
        )

        with self.assertRaises(
            docs.DocumentoError
        ):
            docs.nueva_version(
                self.db,
                1,
                VersionCrearRequest(
                    vigente_desde="2026-01-01"
                ),
                BytesIO(),
                "a.pdf",
                7,
            )

        crear.assert_not_called()
        self.actualizar.assert_not_called()

        self.assertEqual(
            self.documento.id_version_actual,
            10,
        )

        path.unlink.assert_called_once()

    def test_nueva_version_persiste_archivo_chunks_y_version_actual(self):
        contenido = b"contenido-pdf"
        file_hash = docs.sha256(
            contenido
        ).hexdigest()

        path = Mock()
        path.read_bytes.return_value = contenido

        self.mock(
            docs,
            "guardar_pdf",
            return_value=path,
        )

        self.preparar.return_value = (
            file_hash,
            [{"contenido": "Texto"}],
        )

        self.mock(
            docs.repo,
            "siguiente_numero_version",
            return_value="2",
        )

        self.mock(
            docs.repo,
            "crear_version",
            return_value=NS(
                id_version_documento=11
            ),
        )

        orden = []

        self.archivo.side_effect = (
            lambda *a, **k:
            orden.append("archivo")
        )

        self.chunks.side_effect = (
            lambda *a, **k:
            orden.append("chunks")
        )

        self.actualizar.side_effect = (
            lambda *a, **k:
            orden.append("actual")
        )

        self.db.commit.side_effect = (
            lambda:
            orden.append("commit")
        )

        docs.nueva_version(
            self.db,
            1,
            VersionCrearRequest(
                vigente_desde="2026-01-01"
            ),
            BytesIO(),
            "a.pdf",
            7,
        )

        self.assertEqual(
            orden,
            [
                "archivo",
                "chunks",
                "actual",
                "commit",
            ],
        )

        self.assertNotIn(
            "reemplazar",
            self.chunks.call_args.kwargs,
        )

        path.unlink.assert_called_once()

    def test_unidad_inexistente_no_inicia_ingesta(self):
        self.mock(
            docs,
            "obtener_unidad_por_nombre",
            return_value=None,
        )

        with self.assertRaises(
            docs.DocumentoError
        ):
            docs.cargar_documento(
                self.db,
                DocumentoCrearRequest(
                    titulo="Documento",
                    unidad_origen="Inexistente",
                    vigente_desde="2026-01-01",
                ),
                BytesIO(),
                "a.pdf",
                7,
            )

        self.preparar.assert_not_called()

    def test_archivo_falso_y_vacio_rechazados_y_limpiados(self):
        for contenido in (
            b"",
            b"no es PDF",
        ):
            with self.assertRaises(
                docs.DocumentoError
            ):
                docs.guardar_pdf(
                    BytesIO(contenido),
                    "../../nombre.pdf",
                )

        self.assertEqual(
            list(
                Path(
                    self.temporal.name
                ).rglob("*.pdf")
            ),
            [],
        )

    def test_descarga_usa_postgresql_y_verifica_integridad(self):
        contenido = b"pdf almacenado"

        self.version.hash_archivo = (
            docs.sha256(
                contenido
            ).hexdigest()
        )

        obtener = self.mock(
            docs.repo,
            "obtener_archivo_pdf",
            return_value=contenido,
        )

        resultado = docs.descargar_version(
            self.db,
            1,
            10,
        )

        self.assertEqual(
            resultado,
            contenido,
        )

        obtener.assert_called_once_with(
            self.db,
            10,
        )

        self.version.hash_archivo = "hash-distinto"

        with self.assertRaises(
            docs.DocumentoError
        ) as exc:
            docs.descargar_version(
                self.db,
                1,
                10,
            )

        self.assertEqual(
            exc.exception.status_code,
            409,
        )


class ContratosTests(PruebasAisladas):
    def test_pipeline_exige_embeddings_completos_de_512(self):
        self.mock(ingest.Path, 'exists', return_value=True)
        self.mock(ingest, 'calculate_file_hash', return_value='hash')
        self.mock(ingest, 'extract_text_by_page', return_value=[{'page_number': 1, 'text': 'Texto ' * 100}])
        self.mock(ingest, 'normalize_page_text_content', side_effect=lambda x: x)
        self.mock(ingest, 'normalize_pages_text', side_effect=lambda x: x)
        self.mock(ingest, 'split_normative_blocks', return_value=[{
            'content': 'Texto', 'pagina_inicio': 1, 'pagina_fin': 1, 'seccion': None,
            'subseccion': None, 'articulo_numero': None, 'estrategia_chunking': 'normativo',
        }])
        embeddings = self.mock(ingest, 'create_embeddings', return_value=[])
        for respuesta in ([], [[0.0] * 256]):
            embeddings.return_value = respuesta
            with self.assertRaises(ValueError):
                ingest.preparar_chunks('/no-se-abre.pdf')
        embeddings.return_value = [[0.0] * 512]
        _, chunks = ingest.preparar_chunks('/no-se-abre.pdf')
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0]['embedding']), 512)

    def test_retriever_filtra_actual_activa_y_vigente(self):
        self.db.execute.return_value.all.return_value = []
        chunk_repository.search_similar_chunks(self.db, [0.0] * 512)
        sql = str(self.db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
        for fragmento in ('documento_institucional.id_version_actual = version_documento.id_version_documento',
                         'version_documento.vigente_desde', 'version_documento.vigente_hasta >= CURRENT_DATE',
                         'documento_institucional.estado', 'version_documento.estado', 'chunk_documento.activo IS true'):
            self.assertIn(fragmento, sql)

    def test_reemplazo_chunks_usa_delete_acotado_sin_commit_propio(self):
        documento_repository.guardar_chunks(self.db, 10, [], reemplazar=True)
        sql = str(self.db.execute.call_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
        self.assertIn('WHERE chunk_documento.id_version_documento = 10', sql)
        self.db.commit.assert_not_called()

    def test_roles_no_administrativos_rechazados(self):
        permiso = exigir_roles('administrador')
        for nombre in ('solicitante', 'personal_administrativo'):
            usuario = NS(asignaciones_rol=[NS(activo=True, fecha_revocacion=None, rol=NS(activo=True, nombre=nombre))])
            with self.assertRaises(HTTPException) as exc:
                permiso(usuario)
            self.assertEqual(exc.exception.status_code, 403)

    def test_todas_las_rutas_documentales_exigen_administrador(self):
        from app.api.routes.admin_documentos import router
        self.assertEqual(len(router.routes), 8)
        for ruta in router.routes:
            with self.subTest(ruta=ruta.path):
                self.assertIn(exigir_administrador, [d.call for d in ruta.dependant.dependencies])


if __name__ == '__main__':
    unittest.main()
