from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import (
    LOGIN_ATTEMPT_WINDOW_MINUTES,
    MAX_LOGIN_ATTEMPTS,
)
from app.core.security import (
    generar_hash_contrasena,
    utc_now,
    verificar_contrasena,
    verificar_y_actualizar_hash,
)
from app.models.usuario import Usuario
from app.repositories.evento_autenticacion_repository import (
    contar_intentos_fallidos,
)
from app.repositories.usuario_correo_repository import (
    crear_correo,
    existe_correo,
)
from app.repositories.usuario_repository import (
    actualizar_contrasena,
    actualizar_ultimo_acceso,
    crear_usuario,
    obtener_usuario_por_correo,
)
from app.schemas.auth import (
    LoginResponse,
    RegistroRequest,
    RegistroResponse,
)
from app.schemas.usuario import (
    UsuarioAutenticadoResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
    registrar_evento_simple,
)
from app.services.auth.email_verification_service import (
    EnvioVerificacionCorreoError,
    emitir_verificacion_correo,
)
from app.services.auth.role_service import (
    asignar_rol_solicitante,
)
from app.services.auth.session_service import (
    NuevaSesionResultado,
    cerrar_sesion_por_refresh_token,
    preparar_nueva_sesion,
    renovar_sesion,
)
from app.repositories.sesion_usuario_repository import (
    revocar_sesiones_usuario,
)


class AuthServiceError(Exception):
    """Error base del servicio de autenticación."""


class CorreoYaRegistradoError(AuthServiceError):
    """El correo ya está asociado a otra cuenta."""


class CredencialesInvalidasError(AuthServiceError):
    """El correo o la contraseña son incorrectos."""


class CuentaPendienteVerificacionError(AuthServiceError):
    """La cuenta todavía no verificó su correo."""


class CuentaBloqueadaError(AuthServiceError):
    """La cuenta se encuentra bloqueada."""


class CuentaInactivaError(AuthServiceError):
    """La cuenta se encuentra inactiva."""


class DemasiadosIntentosLoginError(AuthServiceError):
    """Se superó el límite temporal de intentos."""


class ContrasenaActualInvalidaError(AuthServiceError):
    """La contraseña actual no es correcta."""


def _normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


def _obtener_roles_activos_usuario(
    usuario: Usuario,
) -> list:
    """
    Obtiene los modelos Rol activos cargados en las
    asignaciones del usuario.
    """
    return [
        asignacion.rol
        for asignacion in usuario.asignaciones_rol
        if (
            asignacion.activo
            and asignacion.fecha_revocacion is None
            and asignacion.rol is not None
            and asignacion.rol.activo
        )
    ]


def _construir_usuario_autenticado(
    usuario: Usuario,
) -> UsuarioAutenticadoResponse:
    """
    Construye una respuesta segura sin exponer el hash de
    contraseña.
    """
    return UsuarioAutenticadoResponse(
        id_usuario=usuario.id_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        estado=usuario.estado,
        fecha_ultimo_acceso=usuario.fecha_ultimo_acceso,
        fecha_creacion=usuario.fecha_creacion,
        fecha_actualizacion=usuario.fecha_actualizacion,
        correos=usuario.correos,
        roles=_obtener_roles_activos_usuario(usuario),
    )


def registrar_usuario(
    db: Session,
    *,
    datos: RegistroRequest,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> RegistroResponse:
    """
    Crea una cuenta, su correo principal y el rol solicitante.

    Después de confirmar la cuenta en PostgreSQL, genera y
    envía el correo de verificación.
    """
    correo_normalizado = _normalizar_correo(
        str(datos.correo)
    )

    if existe_correo(db, correo_normalizado):
        raise CorreoYaRegistradoError(
            "El correo ya se encuentra registrado."
        )

    contrasena_hash = generar_hash_contrasena(
        datos.contrasena.get_secret_value()
    )

    try:
        usuario = crear_usuario(
            db,
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            contrasena_hash=contrasena_hash,
            estado="pendiente_verificacion",
        )

        usuario_correo = crear_correo(
            db,
            id_usuario=usuario.id_usuario,
            correo=correo_normalizado,
            tipo="institucional",
            es_principal=True,
            verificado=False,
        )

        asignar_rol_solicitante(
            db,
            id_usuario=usuario.id_usuario,
        )

        registrar_evento_simple(
            db,
            id_usuario=usuario.id_usuario,
            correo_intentado=correo_normalizado,
            tipo_evento="registro",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=usuario.id_usuario,
            accion="crear_cuenta",
            modulo="autenticacion",
            entidad="usuario",
            id_entidad=usuario.id_usuario,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(usuario)
        db.refresh(usuario_correo)

    except IntegrityError as exc:
        db.rollback()

        raise CorreoYaRegistradoError(
            "El correo ya se encuentra registrado."
        ) from exc

    except Exception:
        db.rollback()
        raise

    mensaje = (
        "La cuenta fue creada. Revisa tu correo para "
        "completar la verificación."
    )

    try:
        emitir_verificacion_correo(
            db,
            usuario_correo=usuario_correo,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

    except EnvioVerificacionCorreoError:
        mensaje = (
            "La cuenta fue creada, pero no fue posible enviar "
            "el correo de verificación. Puedes solicitar un "
            "nuevo envío."
        )

    return RegistroResponse(
        id_usuario=usuario.id_usuario,
        correo=correo_normalizado,
        estado=usuario.estado,
        requiere_verificacion=True,
        mensaje=mensaje,
    )


def iniciar_sesion(
    db: Session,
    *,
    correo: str,
    contrasena: str,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> LoginResponse:
    """
    Valida credenciales, crea una sesión y emite los tokens.
    """
    correo_normalizado = _normalizar_correo(correo)
    ahora = utc_now()

    fecha_inicio_ventana = ahora - timedelta(
        minutes=LOGIN_ATTEMPT_WINDOW_MINUTES
    )

    intentos_fallidos = contar_intentos_fallidos(
        db,
        correo=correo_normalizado,
        fecha_desde=fecha_inicio_ventana,
    )

    if intentos_fallidos >= MAX_LOGIN_ATTEMPTS:
        raise DemasiadosIntentosLoginError(
            "Se superó el número permitido de intentos. "
            "Intenta nuevamente más tarde."
        )

    usuario = obtener_usuario_por_correo(
        db,
        correo_normalizado,
        solo_correo_activo=True,
    )

    if usuario is None:
        registrar_evento_simple(
            db,
            correo_intentado=correo_normalizado,
            tipo_evento="inicio_sesion",
            exitoso=False,
            motivo_fallo="credenciales_invalidas",
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )
        db.commit()

        raise CredencialesInvalidasError(
            "El correo o la contraseña son incorrectos."
        )

    valido, nuevo_hash = verificar_y_actualizar_hash(
        contrasena,
        usuario.contrasena_hash,
    )

    if not valido:
        registrar_evento_simple(
            db,
            id_usuario=usuario.id_usuario,
            correo_intentado=correo_normalizado,
            tipo_evento="inicio_sesion",
            exitoso=False,
            motivo_fallo="credenciales_invalidas",
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )
        db.commit()

        raise CredencialesInvalidasError(
            "El correo o la contraseña son incorrectos."
        )

    if usuario.estado == "pendiente_verificacion":
        raise CuentaPendienteVerificacionError(
            "Debes verificar tu correo antes de iniciar sesión."
        )

    if usuario.estado == "bloqueado":
        raise CuentaBloqueadaError(
            "La cuenta se encuentra bloqueada."
        )

    if usuario.estado != "activo":
        raise CuentaInactivaError(
            "La cuenta no se encuentra habilitada."
        )

    try:
        if nuevo_hash is not None:
            actualizar_contrasena(
                db,
                usuario,
                contrasena_hash=nuevo_hash,
            )

        resultado_sesion: NuevaSesionResultado = (
            preparar_nueva_sesion(
                db,
                usuario=usuario,
                direccion_ip=direccion_ip,
                user_agent=user_agent,
            )
        )

        actualizar_ultimo_acceso(
            db,
            usuario,
            fecha_ultimo_acceso=ahora,
        )

        registrar_evento_simple(
            db,
            id_usuario=usuario.id_usuario,
            correo_intentado=correo_normalizado,
            tipo_evento="inicio_sesion",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(usuario)

        return LoginResponse(
            access_token=resultado_sesion.access_token,
            expires_in=resultado_sesion.expires_in,
            refresh_token=resultado_sesion.refresh_token,
            usuario=_construir_usuario_autenticado(
                usuario
            ),
        )

    except Exception:
        db.rollback()
        raise


def cambiar_contrasena(
    db: Session,
    *,
    usuario: Usuario,
    contrasena_actual: str,
    nueva_contrasena: str,
    identificador_sesion_actual: UUID | None = None,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Cambia la contraseña de un usuario autenticado.

    Se pueden cerrar las demás sesiones y conservar la sesión
    actual mediante su identificador.
    """
    if not verificar_contrasena(
        contrasena_actual,
        usuario.contrasena_hash,
    ):
        raise ContrasenaActualInvalidaError(
            "La contraseña actual no es correcta."
        )

    nueva_hash = generar_hash_contrasena(
        nueva_contrasena
    )
    ahora = utc_now()

    try:
        actualizar_contrasena(
            db,
            usuario,
            contrasena_hash=nueva_hash,
        )

        revocar_sesiones_usuario(
            db,
            id_usuario=usuario.id_usuario,
            fecha_revocacion=ahora,
            motivo_revocacion="cambio_contrasena",
            excluir_identificador=(
                identificador_sesion_actual
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
            accion="cambiar_contrasena",
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