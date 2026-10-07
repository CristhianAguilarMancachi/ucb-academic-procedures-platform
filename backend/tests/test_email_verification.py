"""Pruebas aisladas: no ejecutan SQL, abren conexiones ni envían correos."""
from contextlib import ExitStack
from datetime import timedelta
from types import SimpleNamespace as NS
import ssl
import unittest
from unittest.mock import Mock, patch

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.core.security import utc_now
from app.repositories import token_verificacion_repository as tokens
from app.services.auth import auth_service as auth
from app.services.auth import email_verification_service as verification
from app.services.auth import session_service, user_service
from app.services.email import email_service as email
from app.schemas.auth import RegistroRequest
from app.schemas.correo import CorreoReenviarVerificacionRequest
from app.api.routes import auth as routes


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Engine, 'connect', side_effect=AssertionError('SQL prohibido')))
        self.stack.enter_context(patch('smtplib.SMTP', side_effect=AssertionError('SMTP real prohibido')))
        self.stack.enter_context(patch('smtplib.SMTP_SSL', side_effect=AssertionError('SMTP real prohibido')))
        self.db = Mock()
        self.now = utc_now()
        self.correo = NS(id_usuario_correo=2, id_usuario=1, correo='persona@example.com',
                         activo=True, verificado=False, es_principal=True)
        self.usuario = NS(id_usuario=1, estado='pendiente_verificacion',
                          correo_principal=self.correo, contrasena_hash='hash')
        self.token = NS(id_usuario_correo=2, usuario_correo=self.correo,
                        fecha_utilizacion=None, fecha_revocacion=None,
                        fecha_expiracion=self.now + timedelta(hours=1))

    def mock(self, module, name, **kwargs):
        return self.stack.enter_context(patch.object(module, name, **kwargs))

    def setup_verify(self):
        self.mock(verification, 'obtener_token_verificacion_por_hash', return_value=self.token)
        self.user_lock = self.mock(verification, 'obtener_usuario_por_id', return_value=self.usuario)
        self.mail_lock = self.mock(verification, 'obtener_correo_por_id', return_value=self.correo)
        self.lookup = self.mock(verification, 'obtener_token_verificacion_disponible', return_value=self.token)
        self.mark = self.mock(verification, 'marcar_correo_verificado')
        self.use = self.mock(verification, 'marcar_token_verificacion_utilizado')
        self.revoke = self.mock(verification, 'revocar_tokens_pendientes_correo')
        self.activate = self.mock(verification, 'actualizar_estado_usuario')
        self.event = self.mock(verification, 'registrar_evento_simple')
        self.mock(verification, 'registrar_accion_simple')

    def test_confirmation_locks_and_consumes_before_commit(self):
        self.setup_verify()
        verification.verificar_correo(self.db, token='opaque')
        self.assertTrue(self.user_lock.call_args.kwargs['bloquear'])
        self.assertTrue(self.mail_lock.call_args.kwargs['bloquear'])
        self.assertTrue(self.lookup.call_args.kwargs['bloquear'])
        self.use.assert_called_once()
        self.revoke.assert_called_once()
        self.activate.assert_called_once()
        self.event.assert_called_once()
        self.db.commit.assert_called_once()

    def test_token_state_is_rechecked_after_lock(self):
        self.setup_verify()
        for field in ('fecha_utilizacion', 'fecha_revocacion', 'fecha_expiracion'):
            with self.subTest(field=field):
                old = getattr(self.token, field)
                setattr(self.token, field, self.now - timedelta(seconds=1))
                with self.assertRaises(verification.TokenVerificacionInvalidoError):
                    verification.verificar_correo(self.db, token='opaque')
                setattr(self.token, field, old)
        self.use.assert_not_called()
        self.db.commit.assert_not_called()

    def test_token_consumed_while_waiting_is_rejected(self):
        self.setup_verify()
        self.lookup.return_value = None
        with self.assertRaises(verification.TokenVerificacionInvalidoError):
            verification.verificar_correo(self.db, token='opaque')
        self.use.assert_not_called()

    def test_blocked_and_inactive_accounts_are_not_activated(self):
        self.setup_verify()
        for estado in ('bloqueado', 'inactivo'):
            self.usuario.estado = estado
            verification.verificar_correo(self.db, token='opaque')
        self.activate.assert_not_called()

    def test_secondary_email_does_not_activate_pending_account(self):
        self.setup_verify()
        self.correo.es_principal = False
        verification.verificar_correo(self.db, token='opaque')
        self.activate.assert_not_called()

    def setup_resend(self):
        self.mock(verification, 'obtener_correo_activo_por_direccion', return_value=self.correo)
        self.mock(verification, 'obtener_correo_por_id', return_value=self.correo)
        self.recent = self.mock(verification, 'listar_tokens_correo', return_value=[])
        self.prepare = self.mock(verification, 'preparar_verificacion_correo', return_value=NS(valor='opaque'))
        self.send = self.mock(verification, 'enviar_verificacion_preparada')
        self.revoke = self.mock(verification, 'revocar_tokens_pendientes_correo')

    def test_resend_commits_before_smtp_and_keeps_previous_links(self):
        self.setup_resend()
        self.send.side_effect = lambda **kw: self.db.commit.assert_called_once()
        verification.reenviar_verificacion_correo(self.db, correo=self.correo.correo)
        self.send.assert_called_once()
        self.revoke.assert_not_called()

    def test_failed_resend_does_not_revoke_previous_links(self):
        self.setup_resend()
        self.send.side_effect = verification.EnvioVerificacionCorreoError()
        with self.assertRaises(verification.EnvioVerificacionCorreoError):
            verification.reenviar_verificacion_correo(self.db, correo=self.correo.correo)
        self.db.commit.assert_called_once()
        self.revoke.assert_not_called()

    def test_cooldown_and_hourly_limit(self):
        self.setup_resend()
        for rows in ([NS(fecha_creacion=self.now)],
                     [NS(fecha_creacion=self.now - timedelta(minutes=5))] * 5):
            self.recent.return_value = rows
            verification.reenviar_verificacion_correo(self.db, correo=self.correo.correo)
        self.prepare.assert_not_called()
        self.send.assert_not_called()

    def test_unknown_and_verified_addresses_do_not_send(self):
        self.setup_resend()
        self.correo.verificado = True
        verification.reenviar_verificacion_correo(self.db, correo=self.correo.correo)
        self.mock(verification, 'obtener_correo_activo_por_direccion', return_value=None)
        verification.reenviar_verificacion_correo(self.db, correo='unknown@example.com')
        self.send.assert_not_called()

    def test_public_response_is_generic_even_on_smtp_failure(self):
        send = self.mock(routes, 'reenviar_verificacion_correo')
        request = NS(headers={}, client=NS(host='127.0.0.1'))
        datos = CorreoReenviarVerificacionRequest(correo=self.correo.correo)
        normal = routes.reenviar_verificacion(datos, request, self.db)
        send.side_effect = verification.EnvioVerificacionCorreoError()
        failed = routes.reenviar_verificacion(datos, request, self.db)
        self.assertEqual(normal, failed)
        self.assertIn('Si existe una cuenta pendiente', normal.mensaje)

    def setup_registration(self):
        self.mock(auth, 'existe_correo', return_value=False)
        self.mock(auth, 'generar_hash_contrasena', return_value='hash')
        self.mock(auth, 'crear_usuario', return_value=self.usuario)
        self.mock(auth, 'crear_correo', return_value=self.correo)
        for name in ('asignar_rol_solicitante', 'registrar_accion_simple', 'registrar_evento_simple'):
            self.mock(auth, name)
        self.prepare = self.mock(auth, 'preparar_verificacion_correo', return_value=NS(valor='opaque'))
        self.send = self.mock(auth, 'enviar_verificacion_preparada')
        return RegistroRequest(nombres='Persona', apellidos='Prueba', correo=self.correo.correo,
                               contrasena='password123', confirmar_contrasena='password123')

    def test_registration_token_failure_rolls_back_without_smtp(self):
        datos = self.setup_registration()
        self.prepare.side_effect = RuntimeError('persistencia')
        with self.assertRaises(RuntimeError):
            auth.registrar_usuario(self.db, datos=datos)
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()
        self.send.assert_not_called()

    def test_token_integrity_error_is_not_reported_as_duplicate_email(self):
        datos = self.setup_registration()
        self.prepare.side_effect = IntegrityError('omitted', {}, RuntimeError('constraint'))
        with self.assertRaises(auth.AuthServiceError) as caught:
            auth.registrar_usuario(self.db, datos=datos)
        self.assertNotIsInstance(caught.exception, auth.CorreoYaRegistradoError)
        self.db.commit.assert_not_called()
        self.send.assert_not_called()

    def test_registration_smtp_failure_keeps_pending_account(self):
        datos = self.setup_registration()
        def failed(**kwargs):
            self.db.commit.assert_called_once()
            self.prepare.assert_called_once()
            raise verification.EnvioVerificacionCorreoError()
        self.send.side_effect = failed
        result = auth.registrar_usuario(self.db, datos=datos)
        self.assertEqual(result.estado, 'pendiente_verificacion')
        self.assertIn('no fue posible enviar', result.mensaje)
        self.db.rollback.assert_not_called()

    def test_issuance_is_audit_not_successful_verification(self):
        create = self.mock(verification, 'crear_token_verificacion')
        audit = self.mock(verification, 'registrar_accion_simple')
        event = self.mock(verification, 'registrar_evento_simple')
        token = verification.preparar_verificacion_correo(self.db, usuario_correo=self.correo)
        self.assertNotEqual(token.valor, create.call_args.kwargs['token_hash'])
        self.assertEqual(len(create.call_args.kwargs['token_hash']), 64)
        self.assertEqual(audit.call_args.kwargs['accion'], 'emitir_token_verificacion')
        event.assert_not_called()
        self.db.commit.assert_not_called()

    def test_administrator_cannot_activate_unverified_account(self):
        self.mock(user_service, 'obtener_usuario_por_id', return_value=self.usuario)
        update = self.mock(user_service, 'actualizar_estado_usuario')
        with self.assertRaises(user_service.EstadoUsuarioInvalidoError):
            user_service.cambiar_estado_usuario(self.db, id_usuario=1,
                                               nuevo_estado='activo', id_usuario_actor=3)
        update.assert_not_called()

    def test_active_account_without_verified_email_cannot_login(self):
        self.usuario.estado = 'activo'
        self.mock(auth, 'contar_intentos_fallidos', return_value=0)
        self.mock(auth, 'obtener_usuario_por_correo', return_value=self.usuario)
        self.mock(auth, 'verificar_y_actualizar_hash', return_value=(True, None))
        with self.assertRaises(auth.CuentaPendienteVerificacionError):
            auth.iniciar_sesion(self.db, correo=self.correo.correo, contrasena='password')

    def test_session_guard_requires_verified_principal(self):
        self.usuario.estado = 'activo'
        with self.assertRaises(session_service.UsuarioSesionNoHabilitadoError):
            session_service._validar_usuario_habilitado(self.usuario)
        self.correo.verificado = True
        session_service._validar_usuario_habilitado(self.usuario)

    def test_repository_requests_lock_and_refresh(self):
        tokens.obtener_token_verificacion_disponible(
            self.db, token_hash='hash', fecha_actual=self.now, bloquear=True,
        )
        statement = self.db.scalars.call_args.args[0]
        self.assertIsNotNone(statement._for_update_arg)
        self.assertTrue(statement.get_execution_options()['populate_existing'])

    def test_tls_and_ssl_validate_certificates(self):
        self.mock(email, 'SMTP_HOST', new='smtp.example.com')
        self.mock(email, 'EMAIL_FROM_ADDRESS', new='noreply@example.com')
        self.mock(email, 'SMTP_USERNAME', new='')
        for implicit in (False, True):
            with self.subTest(ssl=implicit), patch.object(email, 'SMTP_USE_TLS', not implicit), \
                    patch.object(email, 'SMTP_USE_SSL', implicit), \
                    patch.object(email.smtplib, 'SMTP') as smtp, \
                    patch.object(email.smtplib, 'SMTP_SSL') as smtp_ssl:
                email.enviar_correo(destinatario='persona@example.com', asunto='Test', contenido_texto='Test')
                context = (smtp_ssl.call_args.kwargs['context'] if implicit else
                           smtp.return_value.__enter__.return_value.starttls.call_args.kwargs['context'])
                self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
                self.assertTrue(context.check_hostname)

    def test_insecure_or_conflicting_smtp_modes_are_rejected(self):
        for enabled in (True, False):
            with patch.object(email, 'SMTP_USE_TLS', enabled), patch.object(email, 'SMTP_USE_SSL', enabled):
                with self.assertRaises(email.EmailServiceError):
                    email.validar_configuracion_email()


if __name__ == '__main__':
    unittest.main()
