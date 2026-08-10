from __future__ import annotations

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Request,
    status,
)

from app.api.routes.auth import (
    obtener_direccion_ip,
    obtener_user_agent,
)
from app.core.dependencies import (
    AccessToken,
    DatabaseSession,
    UsuarioActivo,
)
from app.core.security import (
    TokenSecurityError,
    decodificar_access_token,
)
from app.schemas.sesion import (
    CerrarTodasSesionesRequest,
    CerrarTodasSesionesResponse,
    ListaSesionesResponse,
    SesionRevocarRequest,
    SesionRevocarResponse,
)
from app.schemas.usuario import (
    UsuarioActualizarRequest,
    UsuarioAutenticadoResponse,
)
from app.services.auth.session_service import (
    SesionNoEncontradaError,
    SesionYaRevocadaError,
    cerrar_sesion_por_id,
    cerrar_todas_las_sesiones,
    obtener_sesiones_usuario,
)
from app.services.auth.user_service import (
    ActualizacionUsuarioVaciaError,
    UsuarioNoEncontradoError,
    actualizar_perfil_usuario,
    obtener_perfil_usuario,
)


router = APIRouter(
    prefix="/users",
    tags=["Usuarios"],
)


# ============================================================
# PERFIL
# ============================================================

@router.get(
    "/me",
    response_model=UsuarioAutenticadoResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_perfil(
    usuario: UsuarioActivo,
    db: DatabaseSession,
) -> UsuarioAutenticadoResponse:
    """
    Devuelve el perfil del usuario autenticado junto con sus
    correos y roles activos.
    """
    try:
        return obtener_perfil_usuario(
            db,
            id_usuario=usuario.id_usuario,
        )

    except UsuarioNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/me",
    response_model=UsuarioAutenticadoResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_perfil(
    datos: UsuarioActualizarRequest,
    request: Request,
    usuario: UsuarioActivo,
    db: DatabaseSession,
) -> UsuarioAutenticadoResponse:
    """
    Actualiza los nombres o apellidos del usuario autenticado.
    """
    try:
        return actualizar_perfil_usuario(
            db,
            usuario=usuario,
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except ActualizacionUsuarioVaciaError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except UsuarioNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ============================================================
# SESIONES
# ============================================================

@router.get(
    "/me/sessions",
    response_model=ListaSesionesResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_sesiones(
    usuario: UsuarioActivo,
    db: DatabaseSession,
    solo_vigentes: bool = False,
) -> ListaSesionesResponse:
    """
    Lista las sesiones asociadas al usuario autenticado.
    """
    return obtener_sesiones_usuario(
        db,
        id_usuario=usuario.id_usuario,
        solo_vigentes=solo_vigentes,
    )


@router.delete(
    "/me/sessions/{id_sesion}",
    response_model=SesionRevocarResponse,
    status_code=status.HTTP_200_OK,
)
def cerrar_sesion_especifica(
    id_sesion: int,
    request: Request,
    usuario: UsuarioActivo,
    db: DatabaseSession,
    datos: SesionRevocarRequest | None = Body(
        default=None,
    ),
) -> SesionRevocarResponse:
    """
    Cierra una sesión específica del usuario.

    Sirve, por ejemplo, para cerrar una sesión abierta en otro
    navegador o dispositivo.
    """
    try:
        return cerrar_sesion_por_id(
            db,
            id_usuario=usuario.id_usuario,
            id_sesion=id_sesion,
            motivo=(
                datos.motivo
                if datos is not None
                else None
            ),
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except SesionNoEncontradaError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except SesionYaRevocadaError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete(
    "/me/sessions",
    response_model=CerrarTodasSesionesResponse,
    status_code=status.HTTP_200_OK,
)
def cerrar_sesiones_usuario(
    request: Request,
    usuario: UsuarioActivo,
    token: AccessToken,
    db: DatabaseSession,
    datos: CerrarTodasSesionesRequest | None = Body(
        default=None,
    ),
) -> CerrarTodasSesionesResponse:
    """
    Cierra todas las sesiones del usuario.

    Si se solicita conservar la sesión actual, su identificador
    se obtiene del access token.
    """
    conservar_actual = (
        datos.conservar_sesion_actual
        if datos is not None
        else False
    )

    identificador_actual = None

    if conservar_actual:
        try:
            payload = decodificar_access_token(token)
            identificador_actual = payload.session_id

        except TokenSecurityError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "No fue posible identificar la sesión "
                    "actual."
                ),
                headers={
                    "WWW-Authenticate": "Bearer",
                },
            ) from exc

    return cerrar_todas_las_sesiones(
        db,
        id_usuario=usuario.id_usuario,
        conservar_identificador=identificador_actual,
        direccion_ip=obtener_direccion_ip(request),
        user_agent=obtener_user_agent(request),
    )