from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import FRONTEND_BASE_URL
from app.core.security import (
    crear_token_recuperacion_contrasena,
    generar_hash_contrasena,
    generar_hash_token,
    utc_now,
)
from app.repositories.sesion_usuario_repository import (
    revocar_sesiones_usuario,
)
from app.repositories.token_recuperacion_repository import (
    crear_token_recuperacion,
    marcar_token_recuperacion_utilizado,
    obtener_token_recuperacion_disponible,
    revocar_tokens_pendientes_usuario,
)
from app.repositories.usuario_repository import (
    actualizar_contrasena,
    obtener_usuario_por_correo,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
    registrar_evento_simple,
)
from app.services.email.email_service import (
    EmailServiceError,
    enviar_correo,
)


class PasswordRecoveryServiceError(Exception):
    """Error base del servicio de recuperación."""


class TokenRecuperacionInvalidoError(
    PasswordRecoveryServiceError
):
    """El token no existe, fue utilizado, revocado o expiró."""


class EnvioRecuperacionCorreoError(
    PasswordRecoveryServiceError
):
    """No fue posible enviar el correo de recuperación."""


def _construir_enlace_recuperacion(token: str) -> str:
    return (
        f"{FRONTEND_BASE_URL}/restablecer-contrasena"
        f"?token={token}"
    )


def _enviar_correo_recuperacion(
    *,
    destinatario: str,
    token: str,
) -> None:
    enlace = _construir_enlace_recuperacion(token)

    contenido_texto = (
        "Se solicitó restablecer la contraseña de tu cuenta "
        "del Sistema de Trámites Académicos UCB.\n\n"
        f"Enlace de recuperación:\n{enlace}\n\n"
        "Si no realizaste esta solicitud, puedes ignorar "
        "este mensaje."
    )

    contenido_html = f"""
    <html>
      <body>
        <h2>Recuperación de contraseña</h2>
        <p>
          Se solicitó restablecer la contraseña de tu cuenta.
        </p>
        <p>
          <a href="{enlace}">
            Restablecer contraseña
          </a>
        </p>
        <p>
          Si no realizaste esta solicitud, puedes ignorar
          este mensaje.
        </p>
      </body>
    </html>
    """

    enviar_correo(
        destinatario=destinatario,
        asunto="Recuperación de contraseña",
        contenido_texto=contenido_texto,
        contenido_html=contenido_html,
    )


def solicitar_recuperacion_contrasena(
    db: Session,
    *,
    correo: str,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Solicita la recuperación de contraseña.

    Si el correo no existe, la función no revela esa
    información. La ruta deberá devolver siempre el mismo
    mensaje genérico.
    """
    usuario = obtener_usuario_por_correo(
        db,
        correo,
        solo_correo_activo=True,
    )

    if usuario is None:
        try:
            registrar_evento_simple(
                db,
                correo_intentado=correo,
                tipo_evento="solicitud_recuperacion",
                exitoso=True,
                direccion_ip=direccion_ip,
                user_agent=user_agent,
            )

            db.commit()

        except Exception:
            db.rollback()
            raise

        return

    correo_destino = next(
        (
            item
            for item in usuario.correos
            if (
                item.activo
                and item.es_principal
                and item.verificado
            )
        ),
        None,
    )

    if correo_destino is None:
        correo_destino = next(
            (
                item
                for item in usuario.correos
                if item.activo and item.verificado
            ),
            None,
        )

    if correo_destino is None:
        registrar_evento_simple(
            db,
            id_usuario=usuario.id_usuario,
            correo_intentado=correo,
            tipo_evento="solicitud_recuperacion",
            exitoso=False,
            motivo_fallo="sin_correo_verificado",
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        return

    ahora = utc_now()
    token_generado = crear_token_recuperacion_contrasena()

    try:
        revocar_tokens_pendientes_usuario(
            db,
            id_usuario=usuario.id_usuario,
            fecha_revocacion=ahora,
        )

        crear_token_recuperacion(
            db,
            id_usuario=usuario.id_usuario,
            token_hash=token_generado.hash,
            fecha_expiracion=(
                token_generado.fecha_expiracion
            ),
            direccion_ip_solicitud=direccion_ip,
        )

        registrar_evento_simple(
            db,
            id_usuario=usuario.id_usuario,
            correo_intentado=str(correo_destino.correo),
            tipo_evento="solicitud_recuperacion",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    try:
        _enviar_correo_recuperacion(
            destinatario=str(correo_destino.correo),
            token=token_generado.valor,
        )

    except EmailServiceError as exc:
        raise EnvioRecuperacionCorreoError(
            "El token fue generado, pero no fue posible "
            "enviar el correo de recuperación."
        ) from exc


def restablecer_contrasena(
    db: Session,
    *,
    token: str,
    nueva_contrasena: str,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Valida el token, cambia la contraseña y revoca todas las
    sesiones anteriores de la cuenta.
    """
    ahora = utc_now()
    token_hash = generar_hash_token(token)

    token_registrado = obtener_token_recuperacion_disponible(
        db,
        token_hash=token_hash,
        fecha_actual=ahora,
    )

    if token_registrado is None:
        raise TokenRecuperacionInvalidoError(
            "El token de recuperación no es válido o expiró."
        )

    usuario = token_registrado.usuario

    if usuario is None:
        raise TokenRecuperacionInvalidoError(
            "No se encontró la cuenta asociada al token."
        )

    nueva_contrasena_hash = generar_hash_contrasena(
        nueva_contrasena
    )

    try:
        actualizar_contrasena(
            db,
            usuario,
            contrasena_hash=nueva_contrasena_hash,
        )

        marcar_token_recuperacion_utilizado(
            db,
            token_registrado,
            fecha_utilizacion=ahora,
        )

        revocar_tokens_pendientes_usuario(
            db,
            id_usuario=usuario.id_usuario,
            fecha_revocacion=ahora,
        )

        revocar_sesiones_usuario(
            db,
            id_usuario=usuario.id_usuario,
            fecha_revocacion=ahora,
            motivo_revocacion=(
                "restablecimiento_contrasena"
            ),
        )

        registrar_evento_simple(
            db,
            id_usuario=usuario.id_usuario,
            tipo_evento="cambio_contrasena",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=usuario.id_usuario,
            accion="restablecer_contrasena",
            modulo="autenticacion",
            entidad="usuario",
            id_entidad=usuario.id_usuario,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise