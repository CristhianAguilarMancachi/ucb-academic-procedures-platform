"""Pruebas aisladas de verificación de correo y Brevo."""

from contextlib import ExitStack
from datetime import timedelta
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import requests

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.core.security import utc_now
from app.repositories import (
    token_verificacion_repository as tokens,
)
from app.services.auth import (
    auth_service as auth,
)
from app.services.auth import (
    email_verification_service as verification,
)
from app.services.auth import (
    session_service,
    user_service,
)
from app.services.email import (
    email_service as email,
)
from app.schemas.auth import RegistroRequest
from app.schemas.correo import (
    CorreoReenviarVerificacionRequest,
)
from app.api.routes import (
    auth as routes,
)


class VerificationTests(unittest.TestCase):

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(
            self.stack.close
        )

        self.stack.enter_context(
            patch.object(
                Engine,
                "connect",
                side_effect=AssertionError(
                    "SQL real prohibido"
                ),
            )
        )

        self.stack.enter_context(
            patch.object(
                email.requests,
                "post",
                side_effect=AssertionError(
                    "Brevo real prohibido"
                ),
            )
        )

        self.db = Mock()
        self.now = utc_now()

        self.correo = NS(
            id_usuario_correo=2,
            id_usuario=1,
            correo="persona@example.com",
            activo=True,
            verificado=False,
            es_principal=True,
        )

        self.usuario = NS(
            id_usuario=1,
            estado="pendiente_verificacion",
            correo_principal=self.correo,
            contrasena_hash="hash",
        )

        self.token = NS(
            id_usuario_correo=2,
            usuario_correo=self.correo,
            fecha_utilizacion=None,
            fecha_revocacion=None,
            fecha_expiracion=(
                self.now
                + timedelta(hours=1)
            ),
        )

    def mock(
        self,
        module,
        name,
        **kwargs,
    ):
        return self.stack.enter_context(
            patch.object(
                module,
                name,
                **kwargs,
            )
        )

    def setup_verify(self):
        self.mock(
            verification,
            "obtener_token_verificacion_por_hash",
            return_value=self.token,
        )

        self.user_lock = self.mock(
            verification,
            "obtener_usuario_por_id",
            return_value=self.usuario,
        )

        self.mail_lock = self.mock(
            verification,
            "obtener_correo_por_id",
            return_value=self.correo,
        )

        self.lookup = self.mock(
            verification,
            "obtener_token_verificacion_disponible",
            return_value=self.token,
        )

        self.mock(
            verification,
            "marcar_correo_verificado",
        )

        self.use = self.mock(
            verification,
            "marcar_token_verificacion_utilizado",
        )

        self.revoke = self.mock(
            verification,
            "revocar_tokens_pendientes_correo",
        )

        self.activate = self.mock(
            verification,
            "actualizar_estado_usuario",
        )

        self.event = self.mock(
            verification,
            "registrar_evento_simple",
        )

        self.mock(
            verification,
            "registrar_accion_simple",
        )

    def test_confirmacion_bloquea_y_consume_token(self):
        self.setup_verify()

        verification.verificar_correo(
            self.db,
            token="opaque",
        )

        self.assertTrue(
            self.user_lock
            .call_args
            .kwargs["bloquear"]
        )

        self.assertTrue(
            self.mail_lock
            .call_args
            .kwargs["bloquear"]
        )

        self.assertTrue(
            self.lookup
            .call_args
            .kwargs["bloquear"]
        )

        self.use.assert_called_once()
        self.revoke.assert_called_once()
        self.activate.assert_called_once()
        self.event.assert_called_once()
        self.db.commit.assert_called_once()

    def test_token_invalido_despues_del_bloqueo_es_rechazado(self):
        self.setup_verify()

        for campo in (
            "fecha_utilizacion",
            "fecha_revocacion",
            "fecha_expiracion",
        ):
            with self.subTest(
                campo=campo
            ):
                original = getattr(
                    self.token,
                    campo,
                )

                setattr(
                    self.token,
                    campo,
                    self.now
                    - timedelta(seconds=1),
                )

                with self.assertRaises(
                    verification
                    .TokenVerificacionInvalidoError
                ):
                    verification.verificar_correo(
                        self.db,
                        token="opaque",
                    )

                setattr(
                    self.token,
                    campo,
                    original,
                )

        self.use.assert_not_called()
        self.db.commit.assert_not_called()

    def test_token_consumido_concurrentemente_es_rechazado(self):
        self.setup_verify()

        self.lookup.return_value = None

        with self.assertRaises(
            verification
            .TokenVerificacionInvalidoError
        ):
            verification.verificar_correo(
                self.db,
                token="opaque",
            )

        self.use.assert_not_called()

    def test_cuenta_bloqueada_o_inactiva_no_se_activa(self):
        self.setup_verify()

        for estado in (
            "bloqueado",
            "inactivo",
        ):
            self.usuario.estado = estado

            verification.verificar_correo(
                self.db,
                token="opaque",
            )

        self.activate.assert_not_called()

    def test_correo_secundario_no_activa_cuenta(self):
        self.setup_verify()

        self.correo.es_principal = False

        verification.verificar_correo(
            self.db,
            token="opaque",
        )

        self.activate.assert_not_called()

    def setup_resend(self):
        self.mock(
            verification,
            "obtener_correo_activo_por_direccion",
            return_value=self.correo,
        )

        self.mock(
            verification,
            "obtener_correo_por_id",
            return_value=self.correo,
        )

        self.recent = self.mock(
            verification,
            "listar_tokens_correo",
            return_value=[],
        )

        self.prepare = self.mock(
            verification,
            "preparar_verificacion_correo",
            return_value=NS(
                valor="opaque"
            ),
        )

        self.send = self.mock(
            verification,
            "enviar_verificacion_preparada",
        )

        self.revoke = self.mock(
            verification,
            "revocar_tokens_pendientes_correo",
        )

    def test_reenvio_persiste_token_antes_de_enviar_correo(self):
        self.setup_resend()

        self.send.side_effect = (
            lambda **kwargs:
            self.db.commit.assert_called_once()
        )

        verification.reenviar_verificacion_correo(
            self.db,
            correo=self.correo.correo,
        )

        self.send.assert_called_once()
        self.revoke.assert_not_called()

    def test_fallo_de_correo_no_revoca_enlaces_anteriores(self):
        self.setup_resend()

        self.send.side_effect = (
            verification
            .EnvioVerificacionCorreoError()
        )

        with self.assertRaises(
            verification
            .EnvioVerificacionCorreoError
        ):
            verification.reenviar_verificacion_correo(
                self.db,
                correo=self.correo.correo,
            )

        self.db.commit.assert_called_once()
        self.revoke.assert_not_called()

    def test_limites_de_reenvio(self):
        self.setup_resend()

        casos = (
            [
                NS(
                    fecha_creacion=self.now
                )
            ],
            [
                NS(
                    fecha_creacion=(
                        self.now
                        - timedelta(minutes=5)
                    )
                )
            ] * 5,
        )

        for registros in casos:
            self.recent.return_value = (
                registros
            )

            verification.reenviar_verificacion_correo(
                self.db,
                correo=self.correo.correo,
            )

        self.prepare.assert_not_called()
        self.send.assert_not_called()

    def test_correo_desconocido_o_verificado_no_envia(self):
        self.setup_resend()

        self.correo.verificado = True

        verification.reenviar_verificacion_correo(
            self.db,
            correo=self.correo.correo,
        )

        self.send.assert_not_called()

    def test_respuesta_publica_no_revela_fallo_del_proveedor(self):
        enviar = self.mock(
            routes,
            "reenviar_verificacion_correo",
        )

        request = NS(
            headers={},
            client=NS(
                host="127.0.0.1"
            ),
        )

        datos = (
            CorreoReenviarVerificacionRequest(
                correo=self.correo.correo
            )
        )

        normal = routes.reenviar_verificacion(
            datos,
            request,
            self.db,
        )

        enviar.side_effect = (
            verification
            .EnvioVerificacionCorreoError()
        )

        fallido = routes.reenviar_verificacion(
            datos,
            request,
            self.db,
        )

        self.assertEqual(
            normal,
            fallido,
        )

        self.assertIn(
            "Si existe una cuenta pendiente",
            normal.mensaje,
        )

    def setup_registration(self):
        self.mock(
            auth,
            "existe_correo",
            return_value=False,
        )

        self.mock(
            auth,
            "generar_hash_contrasena",
            return_value="hash",
        )

        self.mock(
            auth,
            "crear_usuario",
            return_value=self.usuario,
        )

        self.mock(
            auth,
            "crear_correo",
            return_value=self.correo,
        )

        for nombre in (
            "asignar_rol_solicitante",
            "registrar_accion_simple",
            "registrar_evento_simple",
        ):
            self.mock(
                auth,
                nombre,
            )

        self.prepare = self.mock(
            auth,
            "preparar_verificacion_correo",
            return_value=NS(
                valor="opaque"
            ),
        )

        self.send = self.mock(
            auth,
            "enviar_verificacion_preparada",
        )

        return RegistroRequest(
            nombres="Persona",
            apellidos="Prueba",
            correo=self.correo.correo,
            contrasena="password123",
            confirmar_contrasena="password123",
        )

    def test_fallo_creando_token_revierte_registro(self):
        datos = self.setup_registration()

        self.prepare.side_effect = (
            RuntimeError(
                "persistencia"
            )
        )

        with self.assertRaises(
            RuntimeError
        ):
            auth.registrar_usuario(
                self.db,
                datos=datos,
            )

        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()
        self.send.assert_not_called()

    def test_error_integridad_token_no_se_reporta_como_correo_duplicado(self):
        datos = self.setup_registration()

        self.prepare.side_effect = (
            IntegrityError(
                "omitted",
                {},
                RuntimeError(
                    "constraint"
                ),
            )
        )

        with self.assertRaises(
            auth.AuthServiceError
        ) as caught:
            auth.registrar_usuario(
                self.db,
                datos=datos,
            )

        self.assertNotIsInstance(
            caught.exception,
            auth.CorreoYaRegistradoError,
        )

        self.db.commit.assert_not_called()
        self.send.assert_not_called()

    def test_fallo_brevo_mantiene_cuenta_pendiente(self):
        datos = self.setup_registration()

        def fallo(**kwargs):
            self.db.commit.assert_called_once()

            raise (
                verification
                .EnvioVerificacionCorreoError()
            )

        self.send.side_effect = fallo

        resultado = auth.registrar_usuario(
            self.db,
            datos=datos,
        )

        self.assertEqual(
            resultado.estado,
            "pendiente_verificacion",
        )

        self.assertIn(
            "no fue posible enviar",
            resultado.mensaje,
        )

        self.db.rollback.assert_not_called()

    def test_emision_token_es_auditoria_no_verificacion_exitosa(self):
        crear = self.mock(
            verification,
            "crear_token_verificacion",
        )

        auditar = self.mock(
            verification,
            "registrar_accion_simple",
        )

        evento = self.mock(
            verification,
            "registrar_evento_simple",
        )

        token = (
            verification
            .preparar_verificacion_correo(
                self.db,
                usuario_correo=self.correo,
            )
        )

        self.assertNotEqual(
            token.valor,
            crear.call_args.kwargs[
                "token_hash"
            ],
        )

        self.assertEqual(
            len(
                crear.call_args.kwargs[
                    "token_hash"
                ]
            ),
            64,
        )

        self.assertEqual(
            auditar.call_args.kwargs[
                "accion"
            ],
            "emitir_token_verificacion",
        )

        evento.assert_not_called()
        self.db.commit.assert_not_called()

    def test_administrador_no_activa_correo_sin_verificar(self):
        self.mock(
            user_service,
            "obtener_usuario_por_id",
            return_value=self.usuario,
        )

        actualizar = self.mock(
            user_service,
            "actualizar_estado_usuario",
        )

        with self.assertRaises(
            user_service
            .EstadoUsuarioInvalidoError
        ):
            user_service.cambiar_estado_usuario(
                self.db,
                id_usuario=1,
                nuevo_estado="activo",
                id_usuario_actor=3,
            )

        actualizar.assert_not_called()

    def test_login_rechaza_cuenta_sin_correo_verificado(self):
        self.usuario.estado = "activo"

        self.mock(
            auth,
            "contar_intentos_fallidos",
            return_value=0,
        )

        self.mock(
            auth,
            "obtener_usuario_por_correo",
            return_value=self.usuario,
        )

        self.mock(
            auth,
            "verificar_y_actualizar_hash",
            return_value=(
                True,
                None,
            ),
        )

        with self.assertRaises(
            auth
            .CuentaPendienteVerificacionError
        ):
            auth.iniciar_sesion(
                self.db,
                correo=self.correo.correo,
                contrasena="password",
            )

    def test_sesion_exige_correo_principal_verificado(self):
        self.usuario.estado = "activo"

        with self.assertRaises(
            session_service
            .UsuarioSesionNoHabilitadoError
        ):
            session_service._validar_usuario_habilitado(
                self.usuario
            )

        self.correo.verificado = True

        session_service._validar_usuario_habilitado(
            self.usuario
        )

    def test_repositorio_bloquea_token_para_actualizacion(self):
        tokens.obtener_token_verificacion_disponible(
            self.db,
            token_hash="hash",
            fecha_actual=self.now,
            bloquear=True,
        )

        statement = (
            self.db
            .scalars
            .call_args
            .args[0]
        )

        self.assertIsNotNone(
            statement._for_update_arg
        )

        self.assertTrue(
            statement
            .get_execution_options()[
                "populate_existing"
            ]
        )


class BrevoTests(unittest.TestCase):

    def test_configuracion_exige_api_key_y_remitente(self):
        with (
            patch.object(
                email,
                "BREVO_API_KEY",
                "",
            ),
            patch.object(
                email,
                "EMAIL_FROM_ADDRESS",
                "",
            ),
        ):
            with self.assertRaises(
                email.EmailServiceError
            ) as caught:
                email.validar_configuracion_email()

        mensaje = str(
            caught.exception
        )

        self.assertIn(
            "BREVO_API_KEY",
            mensaje,
        )

        self.assertIn(
            "EMAIL_FROM",
            mensaje,
        )

    def test_envio_brevo_construye_peticion_correcta(self):
        respuesta = NS(
            status_code=201
        )

        with (
            patch.object(
                email,
                "BREVO_API_KEY",
                "api-test",
            ),
            patch.object(
                email,
                "EMAIL_FROM_ADDRESS",
                "noreply@example.com",
            ),
            patch.object(
                email,
                "EMAIL_FROM_NAME",
                "UCB",
            ),
            patch.object(
                email.requests,
                "post",
                return_value=respuesta,
            ) as post,
        ):
            email.enviar_correo(
                destinatario=(
                    "persona@example.com"
                ),
                asunto="Prueba",
                contenido_texto="Contenido",
            )

        post.assert_called_once()

        argumentos = (
            post.call_args
            .kwargs
        )

        self.assertEqual(
            post.call_args.args[0],
            f"{email.BREVO_API_BASE_URL}/smtp/email",
        )

        self.assertEqual(
            argumentos["headers"][
                "api-key"
            ],
            "api-test",
        )

        self.assertEqual(
            argumentos["json"][
                "sender"
            ]["email"],
            "noreply@example.com",
        )

        self.assertEqual(
            argumentos["json"]["to"][0][
                "email"
            ],
            "persona@example.com",
        )

        self.assertEqual(
            argumentos["timeout"],
            email.BREVO_API_TIMEOUT,
        )

    def test_timeout_brevo_es_error_controlado(self):
        with (
            patch.object(
                email,
                "BREVO_API_KEY",
                "api-test",
            ),
            patch.object(
                email,
                "EMAIL_FROM_ADDRESS",
                "noreply@example.com",
            ),
            patch.object(
                email.requests,
                "post",
                side_effect=requests.Timeout(),
            ),
        ):
            with self.assertRaises(
                email.EmailServiceError
            ):
                email.enviar_correo(
                    destinatario=(
                        "persona@example.com"
                    ),
                    asunto="Prueba",
                    contenido_texto="Texto",
                )

    def test_respuesta_http_brevo_no_exitosa_es_controlada(self):
        with (
            patch.object(
                email,
                "BREVO_API_KEY",
                "api-test",
            ),
            patch.object(
                email,
                "EMAIL_FROM_ADDRESS",
                "noreply@example.com",
            ),
            patch.object(
                email.requests,
                "post",
                return_value=NS(
                    status_code=503
                ),
            ),
        ):
            with self.assertRaises(
                email.EmailServiceError
            ):
                email.enviar_correo(
                    destinatario=(
                        "persona@example.com"
                    ),
                    asunto="Prueba",
                    contenido_texto="Texto",
                )


if __name__ == "__main__":
    unittest.main()
