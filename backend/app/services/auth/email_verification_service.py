
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import (
    EMAIL_VERIFICATION_EXPIRE_MINUTES,
    FRONTEND_BASE_URL,
)
from app.core.security import (
    crear_token_verificacion_correo,
    generar_hash_token,
    utc_now,
)
from app.models.usuario_correo import UsuarioCorreo
from app.repositories.token_verificacion_repository import (
    crear_token_verificacion,
    listar_tokens_correo,
    obtener_token_verificacion_por_hash,
    marcar_token_verificacion_utilizado,
    obtener_token_verificacion_disponible,
    revocar_tokens_pendientes_correo,
)
from app.repositories.usuario_correo_repository import (
    marcar_correo_verificado,
    obtener_correo_activo_por_direccion,
    obtener_correo_por_id,
)
from app.repositories.usuario_repository import (
    actualizar_estado_usuario,
    obtener_usuario_por_id,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
    registrar_evento_simple,
)
from app.schemas.tokens import TokenGenerado
from app.services.email.email_service import (
    EmailServiceError,
    construir_html_institucional,
    enviar_correo,
)


logger = logging.getLogger(__name__)
REENVIO_ESPERA_SEGUNDOS = 60
MAX_EMISIONES_POR_HORA = 5


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

    vigencia = EMAIL_VERIFICATION_EXPIRE_MINUTES
    if vigencia % 60 == 0:
        horas = vigencia // 60
        duracion = (
            f"{horas} hora"
            if horas == 1
            else f"{horas} horas"
        )
    else:
        duracion = f"{vigencia} minutos"

    asunto = (
        "Verifica tu correo — "
        "Sistema de Trámites Académicos UCB"
    )

    parrafos = [
        (
            "Recibimos una solicitud para registrar una "
            "cuenta en el Sistema de Trámites Académicos "
            "de la UCB — Sede La Paz."
        ),
        (
            "Para confirmar que esta dirección de correo "
            "te pertenece y activar tu cuenta, selecciona "
            "el botón de verificación."
        ),
        f"El enlace tiene una vigencia de {duracion}.",
    ]

    aviso = (
        "Si no realizaste este registro, ignora "
        "el mensaje. No necesitas realizar ninguna acción."
    )

    contenido_texto = (
        "Verificación de correo — Sistema de Trámites "
        "Académicos UCB\n\n"
        + "\n\n".join(parrafos)
        + f"\n\nVerificar correo:\n{enlace}\n\n"
        + aviso
    )

    contenido_html = construir_html_institucional(
        titulo="Verifica tu correo electrónico",
        parrafos=parrafos,
        texto_accion="Verificar mi correo",
        url_accion=enlace,
        aviso=aviso,
    )

    enviar_correo(
        destinatario=destinatario,
        asunto=asunto,
        contenido_texto=contenido_texto,
        contenido_html=contenido_html,
    )


def preparar_verificacion_correo(
    db: Session,
    *,
    usuario_correo: UsuarioCorreo,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TokenGenerado:
    """Persiste el token sin commit ni SMTP.

    Los enlaces anteriores siguen válidos hasta su expiración
    o hasta confirmar el correo. Así un fallo de envío no
    invalida un enlace ya recibido.
    """
    if not usuario_correo.activo:
        raise CorreoNoEncontradoError(
            "El correo se encuentra inactivo."
        )

    if usuario_correo.verificado:
        raise CorreoYaVerificadoError(
            "El correo ya se encuentra verificado."
        )

    token = crear_token_verificacion_correo()

    crear_token_verificacion(
        db,
        id_usuario_correo=usuario_correo.id_usuario_correo,
        token_hash=token.hash,
        fecha_expiracion=token.fecha_expiracion,
        direccion_ip_solicitud=direccion_ip,
    )

    registrar_accion_simple(
        db,
        accion="emitir_token_verificacion",
        modulo="autenticacion",
        entidad="usuario_correo",
        id_entidad=usuario_correo.id_usuario_correo,
        direccion_ip=direccion_ip,
        user_agent=user_agent,
    )

    return token


def enviar_verificacion_preparada(
    *,
    destinatario: str,
    token: str,
) -> None:
    """Realiza el envío después del commit de la cuenta."""
    try:
        _enviar_correo_verificacion(
            destinatario=destinatario,
            token=token,
        )

    except EmailServiceError as exc:
        logger.warning(
            "No fue posible enviar el correo "
            "de verificación por SMTP."
        )
        raise EnvioVerificacionCorreoError(
            "No fue posible enviar el correo de verificación."
        ) from exc

    logger.info(
        "Correo de verificación aceptado por SMTP; "
        "pendiente de confirmación."
    )


def reenviar_verificacion_correo(
    db: Session,
    *,
    correo: str,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Respuesta neutra para cuentas inexistentes o verificadas.

    El bloqueo del correo serializa reenvíos.
    Se cuentan también emisiones cuyo envío falló.
    """
    try:
        encontrado = obtener_correo_activo_por_direccion(
            db,
            correo.strip().lower(),
        )

        if encontrado is None:
            db.rollback()
            return

        usuario_correo = obtener_correo_por_id(
            db,
            encontrado.id_usuario_correo,
            bloquear=True,
        )

        if (
            usuario_correo is None
            or not usuario_correo.activo
            or usuario_correo.verificado
        ):
            db.rollback()
            return

        ahora = utc_now()

        recientes = listar_tokens_correo(
            db,
            usuario_correo.id_usuario_correo,
            desde=ahora - timedelta(hours=1),
        )

        if (
            len(recientes) >= MAX_EMISIONES_POR_HORA
            or any(
                token.fecha_creacion
                > ahora - timedelta(
                    seconds=REENVIO_ESPERA_SEGUNDOS
                )
                for token in recientes
            )
        ):
            db.rollback()
            return

        token = preparar_verificacion_correo(
            db,
            usuario_correo=usuario_correo,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        destinatario = str(usuario_correo.correo)
        db.commit()

    except Exception:
        db.rollback()
        raise

    enviar_verificacion_preparada(
        destinatario=destinatario,
        token=token.valor,
    )


def verificar_correo(
    db: Session,
    *,
    token: str,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UsuarioCorreo:
    """
    Verifica el token y activa la cuenta pendiente.
    """
    token_hash = generar_hash_token(token)

    try:
        referencia = obtener_token_verificacion_por_hash(
            db,
            token_hash,
        )

        if (
            referencia is None
            or referencia.usuario_correo is None
        ):
            raise TokenVerificacionInvalidoError(
                "El enlace no es válido o expiró."
            )

        usuario = obtener_usuario_por_id(
            db,
            referencia.usuario_correo.id_usuario,
            bloquear=True,
        )

        usuario_correo = obtener_correo_por_id(
            db,
            referencia.id_usuario_correo,
            bloquear=True,
        )

        token_registrado = obtener_token_verificacion_disponible(
            db,
            token_hash=token_hash,
            fecha_actual=utc_now(),
            bloquear=True,
        )

        ahora = utc_now()

        if (
            token_registrado is None
            or token_registrado.fecha_utilizacion is not None
            or token_registrado.fecha_revocacion is not None
            or token_registrado.fecha_expiracion <= ahora
        ):
            raise TokenVerificacionInvalidoError(
                "El enlace no es válido o expiró."
            )

        if (
            usuario_correo is None
            or not usuario_correo.activo
            or usuario is None
        ):
            raise CorreoNoEncontradoError(
                "No se encontró el correo asociado al enlace."
            )

        if usuario_correo.verificado:
            raise CorreoYaVerificadoError(
                "El correo ya se encuentra verificado."
            )

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

        revocar_tokens_pendientes_correo(
            db,
            id_usuario_correo=usuario_correo.id_usuario_correo,
            fecha_revocacion=ahora,
        )

        cuenta_activada = (
            usuario.estado == "pendiente_verificacion"
            and usuario_correo.es_principal
        )

        if cuenta_activada:
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
            id_entidad=usuario_correo.id_usuario_correo,
            detalle={
                "correo": str(usuario_correo.correo),
                "cuenta_activada": cuenta_activada,
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
