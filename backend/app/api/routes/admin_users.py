from __future__ import annotations

from typing import Literal

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
    status,
)

from app.api.routes.auth import (
    obtener_direccion_ip,
    obtener_user_agent,
)
from app.core.dependencies import (
    AdministradorActual,
    DatabaseSession,
)
from app.schemas.rol import (
    ListaRolesResponse,
    RolAsignarRequest,
    RolResponse,
    RolRevocarRequest,
    UsuarioRolResponse,
)
from app.schemas.usuario import (
    ListaUsuariosResponse,
    UsuarioAdministradorDetalleResponse,
    UsuarioEstadoActualizarRequest,
)
from app.services.auth.role_service import (
    RolNoAsignadoError,
    RolNoEncontradoError,
    RolYaAsignadoError,
    RoleServiceError,
    UsuarioNoEncontradoError as UsuarioRolNoEncontradoError,
    asignar_rol_usuario,
    obtener_roles_disponibles,
    revocar_rol_usuario,
)
from app.services.auth.user_service import (
    EstadoUsuarioInvalidoError,
    UsuarioNoEncontradoError,
    cambiar_estado_usuario,
    listar_usuarios_administracion,
    obtener_usuario_administracion,
)


router = APIRouter(
    prefix="/admin/users",
    tags=["Administración de usuarios"],
)


EstadoUsuarioFiltro = Literal[
    "pendiente_verificacion",
    "activo",
    "bloqueado",
    "inactivo",
]


# ============================================================
# USUARIOS
# ============================================================

@router.get(
    "",
    response_model=ListaUsuariosResponse,
    status_code=status.HTTP_200_OK,
)
def listar_usuarios(
    administrador: AdministradorActual,
    db: DatabaseSession,
    pagina: int = Query(
        default=1,
        ge=1,
    ),
    por_pagina: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    estado: EstadoUsuarioFiltro | None = Query(
        default=None,
    ),
    busqueda: str | None = Query(
        default=None,
        min_length=1,
        max_length=150,
    ),
) -> ListaUsuariosResponse:
    """
    Lista usuarios con filtros y paginación.

    Solo puede utilizarlo un administrador.
    """
    return listar_usuarios_administracion(
        db,
        pagina=pagina,
        por_pagina=por_pagina,
        estado=estado,
        texto_busqueda=busqueda,
    )


# ============================================================
# CATÁLOGOS
# ============================================================

@router.get(
    "/catalog/roles",
    response_model=ListaRolesResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_roles_disponibles(
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> ListaRolesResponse:
    """
    Lista los roles activos que pueden asignarse.
    """
    roles = obtener_roles_disponibles(db)

    items = [
        RolResponse.model_validate(rol)
        for rol in roles
    ]

    return ListaRolesResponse(
        items=items,
        total=len(items),
    )


# ============================================================
# DETALLE Y ESTADO DE USUARIO
# ============================================================

@router.get(
    "/{id_usuario}",
    response_model=UsuarioAdministradorDetalleResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_usuario(
    id_usuario: int,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> UsuarioAdministradorDetalleResponse:
    """
    Devuelve el detalle administrativo de un usuario.
    """
    try:
        return obtener_usuario_administracion(
            db,
            id_usuario=id_usuario,
        )

    except UsuarioNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{id_usuario}/status",
    response_model=UsuarioAdministradorDetalleResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_estado_usuario(
    id_usuario: int,
    datos: UsuarioEstadoActualizarRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> UsuarioAdministradorDetalleResponse:
    """
    Bloquea, activa, desactiva o devuelve una cuenta al estado
    pendiente de verificación.

    Al bloquear o desactivar una cuenta se revocan todas sus
    sesiones.
    """
    try:
        return cambiar_estado_usuario(
            db,
            id_usuario=id_usuario,
            nuevo_estado=datos.estado,
            id_usuario_actor=administrador.id_usuario,
            motivo=datos.motivo,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except UsuarioNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except EstadoUsuarioInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# ROLES DEL USUARIO
# ============================================================

@router.post(
    "/{id_usuario}/roles",
    response_model=UsuarioRolResponse,
    status_code=status.HTTP_201_CREATED,
)
def asignar_rol(
    id_usuario: int,
    datos: RolAsignarRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> UsuarioRolResponse:
    """
    Asigna un rol activo a un usuario.
    """
    try:
        asignacion = asignar_rol_usuario(
            db,
            id_usuario=id_usuario,
            id_rol=datos.id_rol,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

        return UsuarioRolResponse.model_validate(
            asignacion
        )

    except UsuarioRolNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except RolNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except RolYaAsignadoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except RoleServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{id_usuario}/roles/{id_rol}",
    response_model=UsuarioRolResponse,
    status_code=status.HTTP_200_OK,
)
def revocar_rol(
    id_usuario: int,
    id_rol: int,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
    datos: RolRevocarRequest | None = None,
) -> UsuarioRolResponse:
    """
    Revoca un rol asignado a un usuario.
    """
    try:
        asignacion = revocar_rol_usuario(
            db,
            id_usuario=id_usuario,
            id_rol=id_rol,
            id_usuario_actor=administrador.id_usuario,
            motivo=(
                datos.motivo
                if datos is not None
                else None
            ),
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

        return UsuarioRolResponse.model_validate(
            asignacion
        )

    except UsuarioRolNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except RolNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except RolNoAsignadoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except RoleServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc