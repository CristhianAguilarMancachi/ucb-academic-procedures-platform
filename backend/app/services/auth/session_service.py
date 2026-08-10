from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.security import (
    crear_access_token,
    crear_refresh_token,
    generar_hash_token,
    utc_now,
)
from app.models.sesion_usuario import SesionUsuario
from app.models.usuario import Usuario
from app.repositories.sesion_usuario_repository import (
    actualizar_actividad_sesion,
    crear_sesion,
    listar_sesiones_usuario,
    obtener_sesion_por_id,
    obtener_sesion_por_refresh_hash,
    obtener_sesion_vigente_por_refresh_hash,
    revocar_sesion,
    revocar_sesiones_usuario,
    rotar_refresh_token,
)
from app.repositories.usuario_rol_repository import (
    obtener_nombres_roles_activos,
)
from app.schemas.sesion import (
    CerrarTodasSesionesResponse,
    ListaSesionesResponse,
    SesionResumenResponse,
    SesionRevocarResponse,
)
from app.schemas.tokens import TokenRotacionResponse
from app.services.auth.audit_service import (
    registrar_evento_simple,
)


class SessionServiceError(Exception):
    """
    Error base del servicio de sesiones.
    """


class RefreshTokenInvalidoError(SessionServiceError):
    """
    El refresh token no existe, fue revocado o expiró.
    """


class SesionNoEncontradaError(SessionServiceError):
    """
    No existe la sesión solicitada o no pertenece al usuario.
    """


class SesionYaRevocadaError(SessionServiceError):
    """
    La sesión ya había sido cerrada.
    """


class UsuarioSesionNoHabilitadoError(SessionServiceError):
    """
    La cuenta asociada a la sesión no está habilitada.
    """


@dataclass(slots=True)
class NuevaSesionResultado:
    """
    Resultado interno de la creación de una sesión.

    Se utiliza desde auth_service.py durante el login.
    """

    sesion: SesionUsuario
    access_token: str
    refresh_token: str
    expires_in: int


def _validar_usuario_habilitado(
    usuario: Usuario,
) -> None:
    """
    Comprueba que la cuenta pueda utilizar sesiones.
    """
    if usuario.estado != "activo":
        raise UsuarioSesionNoHabilitadoError(
            "La cuenta no está habilitada para iniciar sesión."
        )


def preparar_nueva_sesion(
    db: Session,
    *,
    usuario: Usuario,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> NuevaSesionResultado:
    """
    Crea una sesión y genera sus tokens sin hacer commit.

    AuthService utilizará esta función para incluir la sesión,
    el evento de login y la actualización del último acceso
    dentro de una sola transacción.
    """
    _validar_usuario_habilitado(usuario)

    identificador_sesion = uuid4()
    refresh_generado = crear_refresh_token()

    roles = obtener_nombres_roles_activos(
        db,
        usuario.id_usuario,
    )

    sesion = crear_sesion(
        db,
        id_usuario=usuario.id_usuario,
        identificador_sesion=identificador_sesion,
        refresh_token_hash=refresh_generado.hash,
        fecha_expiracion=refresh_generado.fecha_expiracion,
        direccion_ip=direccion_ip,
        user_agent=user_agent,
    )

    access_token, _ = crear_access_token(
        id_usuario=usuario.id_usuario,
        identificador_sesion=identificador_sesion,
        roles=roles,
    )

    return NuevaSesionResultado(
        sesion=sesion,
        access_token=access_token,
        refresh_token=refresh_generado.valor,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def renovar_sesion(
    db: Session,
    *,
    refresh_token: str,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TokenRotacionResponse:
    """
    Renueva una sesión mediante rotación del refresh token.

    El token anterior deja de funcionar porque su hash es
    sustituido por el hash del nuevo refresh token.
    """
    ahora = utc_now()
    token_hash = generar_hash_token(refresh_token)

    sesion = obtener_sesion_vigente_por_refresh_hash(
        db,
        refresh_token_hash=token_hash,
        fecha_actual=ahora,
    )

    if sesion is None:
        raise RefreshTokenInvalidoError(
            "El refresh token no es válido o ha expirado."
        )

    usuario = sesion.usuario

    if usuario is None:
        raise RefreshTokenInvalidoError(
            "No se encontró el usuario asociado a la sesión."
        )

    _validar_usuario_habilitado(usuario)

    nuevo_refresh = crear_refresh_token()

    roles = obtener_nombres_roles_activos(
        db,
        usuario.id_usuario,
    )

    access_token, _ = crear_access_token(
        id_usuario=usuario.id_usuario,
        identificador_sesion=sesion.identificador_sesion,
        roles=roles,
    )

    try:
        rotar_refresh_token(
            db,
            sesion,
            nuevo_refresh_token_hash=nuevo_refresh.hash,
            nueva_fecha_expiracion=(
                nuevo_refresh.fecha_expiracion
            ),
            fecha_actividad=ahora,
        )

        if direccion_ip is not None:
            sesion.direccion_ip = direccion_ip

        if user_agent is not None:
            sesion.user_agent = user_agent

        registrar_evento_simple(
            db,
            id_usuario=usuario.id_usuario,
            tipo_evento="renovacion_sesion",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        return TokenRotacionResponse(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=nuevo_refresh.valor,
        )

    except Exception:
        db.rollback()
        raise


def cerrar_sesion_por_refresh_token(
    db: Session,
    *,
    refresh_token: str,
    motivo: str = "cierre_sesion",
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SesionRevocarResponse:
    """
    Cierra la sesión correspondiente al refresh token.
    """
    token_hash = generar_hash_token(refresh_token)

    sesion = obtener_sesion_por_refresh_hash(
        db,
        token_hash,
        cargar_usuario=False,
    )

    if sesion is None:
        raise RefreshTokenInvalidoError(
            "No se encontró la sesión indicada."
        )

    if sesion.fecha_revocacion is not None:
        raise SesionYaRevocadaError(
            "La sesión ya se encuentra cerrada."
        )

    ahora = utc_now()

    try:
        revocar_sesion(
            db,
            sesion,
            fecha_revocacion=ahora,
            motivo_revocacion=motivo,
        )

        registrar_evento_simple(
            db,
            id_usuario=sesion.id_usuario,
            tipo_evento="cierre_sesion",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(sesion)

        return SesionRevocarResponse(
            id_sesion=sesion.id_sesion,
            identificador_sesion=(
                sesion.identificador_sesion
            ),
            fecha_revocacion=sesion.fecha_revocacion,
            mensaje="La sesión fue cerrada correctamente.",
        )

    except Exception:
        db.rollback()
        raise


def cerrar_sesion_por_id(
    db: Session,
    *,
    id_usuario: int,
    id_sesion: int,
    motivo: str | None = None,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SesionRevocarResponse:
    """
    Permite al usuario cerrar una de sus sesiones por ID.
    """
    sesion = obtener_sesion_por_id(
        db,
        id_sesion,
    )

    if (
        sesion is None
        or sesion.id_usuario != id_usuario
    ):
        raise SesionNoEncontradaError(
            "La sesión indicada no existe."
        )

    if sesion.fecha_revocacion is not None:
        raise SesionYaRevocadaError(
            "La sesión ya se encuentra cerrada."
        )

    ahora = utc_now()

    try:
        revocar_sesion(
            db,
            sesion,
            fecha_revocacion=ahora,
            motivo_revocacion=(
                motivo or "revocada_por_usuario"
            ),
        )

        registrar_evento_simple(
            db,
            id_usuario=id_usuario,
            tipo_evento="cierre_sesion",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(sesion)

        return SesionRevocarResponse(
            id_sesion=sesion.id_sesion,
            identificador_sesion=(
                sesion.identificador_sesion
            ),
            fecha_revocacion=sesion.fecha_revocacion,
            mensaje="La sesión fue cerrada correctamente.",
        )

    except Exception:
        db.rollback()
        raise


def cerrar_todas_las_sesiones(
    db: Session,
    *,
    id_usuario: int,
    conservar_identificador: UUID | None = None,
    motivo: str = "cierre_todas_sesiones",
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> CerrarTodasSesionesResponse:
    """
    Revoca todas las sesiones de una cuenta.

    Puede conservar la sesión desde la que se realiza la
    operación.
    """
    ahora = utc_now()

    try:
        cantidad = revocar_sesiones_usuario(
            db,
            id_usuario=id_usuario,
            fecha_revocacion=ahora,
            motivo_revocacion=motivo,
            excluir_identificador=conservar_identificador,
        )

        registrar_evento_simple(
            db,
            id_usuario=id_usuario,
            tipo_evento="cierre_sesion",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        return CerrarTodasSesionesResponse(
            sesiones_revocadas=cantidad,
            sesion_actual_conservada=(
                conservar_identificador is not None
            ),
            mensaje=(
                "Las sesiones fueron cerradas correctamente."
            ),
        )

    except Exception:
        db.rollback()
        raise


def obtener_sesiones_usuario(
    db: Session,
    *,
    id_usuario: int,
    solo_vigentes: bool = False,
) -> ListaSesionesResponse:
    """
    Obtiene las sesiones pertenecientes a un usuario.
    """
    sesiones = listar_sesiones_usuario(
        db,
        id_usuario,
        solo_vigentes=solo_vigentes,
        fecha_actual=(
            utc_now()
            if solo_vigentes
            else None
        ),
    )

    items = [
        SesionResumenResponse.model_validate(
            sesion
        )
        for sesion in sesiones
    ]

    return ListaSesionesResponse(
        items=items,
        total=len(items),
    )


def actualizar_actividad(
    db: Session,
    *,
    sesion: SesionUsuario,
) -> SesionUsuario:
    """
    Actualiza la fecha de actividad de una sesión.

    No hace commit porque puede utilizarse dentro de otra
    operación autenticada.
    """
    return actualizar_actividad_sesion(
        db,
        sesion,
        fecha_actividad=utc_now(),
    )