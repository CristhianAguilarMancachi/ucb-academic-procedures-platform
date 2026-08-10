from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import FRONTEND_BASE_URL
from app.core.security import (
    crear_token_verificacion_correo,
    generar_hash_token,
    utc_now,
)
from app.models.usuario_correo import UsuarioCorreo
from app.repositories.token_verificacion_repository import (
    crear_token_verificacion,
    marcar_token_verificacion_utilizado,
    obtener_token_verificacion_disponible,
    revocar_tokens_pendientes_correo,
)
from app.repositories.usuario_correo_repository import (
    marcar_correo_verificado,
    obtener_correo_activo_por_direccion,
)
from app.repositories.usuario_repository import (
    actualizar_estado_usuario,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
    registrar_evento_simple,
)
from app.services.email.email_service import (
    EmailServiceError,
    enviar_correo,
)


class EmailVerificationServiceError(Exception):
    """Error base del servicio de verificación de correo."""


class CorreoNoEncontradoError(EmailVerificationServiceError):
    """El correo indicado no existe o está inactivo."""


class CorreoYaVerificadoError(EmailVerificationServiceError):
    """El correo ya fue verificado anteriormente."""


class TokenVerificacionInvalidoError(
    EmailVerificationServiceError
):
    """El token no existe, expiró, fue revocado o ya se utilizó."""


class EnvioVerificacionCorreoError(
    EmailVerificationServiceError
):
    """No fue posible enviar el correo de verificación."""


def _construir_enlace_verificacion(token: str) -> str:
    return (
        f"{FRONTEND_BASE_URL}/verificar-correo"
        f"?token={token}"
    )


def _enviar_correo_verificacion(
    *,
    destinatario: str,
    token: str,
) -> None:
    enlace = _construir_enlace_verificacion(token)

    contenido_texto = (
        "Confirma tu correo electrónico para activar tu cuenta "
        "en el Sistema de Trámites Académicos UCB.\n\n"
        f"Enlace de verificación:\n{enlace}\n\n"
        "Si no realizaste este registro, puedes ignorar "
        "este mensaje."
    )

    contenido_html = f"""
    <html>
      <body>
        <h2>Verificación de correo</h2>
        <p>
          Confirma tu correo electrónico para activar tu cuenta
          en el Sistema de Trámites Académicos UCB.
        </p>
        <p>
          <a href="{enlace}">
            Verificar correo electrónico
          </a>
        </p>
        <p>
          Si no realizaste este registro, puedes ignorar
          este mensaje.
        </p>
      </body>
    </html>
    """

    enviar_correo(
        destinatario=destinatario,
        asunto="Verifica tu correo electrónico",
        contenido_texto=contenido_texto,
        contenido_html=contenido_html,
    )


def emitir_verificacion_correo(
    db: Session,
    *,
    usuario_correo: UsuarioCorreo,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Genera un token de verificación y envía el enlace.

    La creación del token se confirma antes de intentar enviar
    el correo. Así, si el servidor SMTP falla, la cuenta y el
    token no se pierden y se puede solicitar un reenvío.
    """
    if not usuario_correo.activo:
        raise CorreoNoEncontradoError(
            "El correo indicado se encuentra inactivo."
        )

    if usuario_correo.verificado:
        raise CorreoYaVerificadoError(
            "El correo ya se encuentra verificado."
        )

    ahora = utc_now()
    token_generado = crear_token_verificacion_correo()

    try:
        revocar_tokens_pendientes_correo(
            db,
            id_usuario_correo=(
                usuario_correo.id_usuario_correo
            ),
            fecha_revocacion=ahora,
        )

        crear_token_verificacion(
            db,
            id_usuario_correo=(
                usuario_correo.id_usuario_correo
            ),
            token_hash=token_generado.hash,
            fecha_expiracion=(
                token_generado.fecha_expiracion
            ),
            direccion_ip_solicitud=direccion_ip,
        )

        registrar_evento_simple(
            db,
            id_usuario=usuario_correo.id_usuario,
            correo_intentado=str(usuario_correo.correo),
            tipo_evento="verificacion_correo",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    try:
        _enviar_correo_verificacion(
            destinatario=str(usuario_correo.correo),
            token=token_generado.valor,
        )

    except EmailServiceError as exc:
        raise EnvioVerificacionCorreoError(
            "El token fue generado, pero no fue posible "
            "enviar el correo de verificación."
        ) from exc


def reenviar_verificacion_correo(
    db: Session,
    *,
    correo: str,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Genera un nuevo token para un correo pendiente.
    """
    usuario_correo = obtener_correo_activo_por_direccion(
        db,
        correo,
    )

    if usuario_correo is None:
        raise CorreoNoEncontradoError(
            "No se encontró el correo indicado."
        )

    emitir_verificacion_correo(
        db,
        usuario_correo=usuario_correo,
        direccion_ip=direccion_ip,
        user_agent=user_agent,
    )


def verificar_correo(
    db: Session,
    *,
    token: str,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UsuarioCorreo:
    """
    Valida el token, verifica el correo y activa la cuenta
    cuando todavía estaba pendiente de verificación.
    """
    ahora = utc_now()
    token_hash = generar_hash_token(token)

    token_registrado = obtener_token_verificacion_disponible(
        db,
        token_hash=token_hash,
        fecha_actual=ahora,
    )

    if token_registrado is None:
        raise TokenVerificacionInvalidoError(
            "El token de verificación no es válido o expiró."
        )

    usuario_correo = token_registrado.usuario_correo

    if usuario_correo is None or not usuario_correo.activo:
        raise CorreoNoEncontradoError(
            "No se encontró el correo asociado al token."
        )

    if usuario_correo.verificado:
        raise CorreoYaVerificadoError(
            "El correo ya se encuentra verificado."
        )

    usuario = usuario_correo.usuario

    if usuario is None:
        raise EmailVerificationServiceError(
            "No se encontró la cuenta asociada al correo."
        )

    try:
        marcar_correo_verificado(
            db,
            usuario_correo,
            fecha_verificacion=ahora,
        )

        marcar_token_verificacion_utilizado(
            db,
            token_registrado,
            fecha_utilizacion=ahora,
        )

        if usuario.estado == "pendiente_verificacion":
            actualizar_estado_usuario(
                db,
                usuario,
                estado="activo",
            )

        registrar_evento_simple(
            db,
            id_usuario=usuario.id_usuario,
            correo_intentado=str(usuario_correo.correo),
            tipo_evento="verificacion_correo",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=usuario.id_usuario,
            accion="verificar_correo",
            modulo="autenticacion",
            entidad="usuario_correo",
            id_entidad=(
                usuario_correo.id_usuario_correo
            ),
            detalle={
                "correo": str(usuario_correo.correo),
                "cuenta_activada": (
                    usuario.estado == "activo"
                ),
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(usuario_correo)

        return usuario_correo

    except Exception:
        db.rollback()
        raise