from __future__ import annotations

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
from app.schemas.gestion_seguimiento.unidad import (
    ListaUnidadesResponse,
    UnidadActualizarRequest,
    UnidadCrearRequest,
    UnidadDetalleResponse,
    UnidadResponse,
    UsuarioUnidadAsignarRequest,
    UsuarioUnidadResponse,
)
from app.services.gestion_seguimiento.unidad_service import (
    ActualizacionUnidadVaciaError,
    UnidadDuplicadaError,
    UnidadNoEncontradaError,
    UnidadServiceError,
    UsuarioNoEncontradoError,
    UsuarioSinRolAdministrativoError,
    UsuarioUnidadNoAsignadaError,
    UsuarioUnidadYaAsignadaError,
    actualizar_unidad_administrativa,
    asignar_usuario_unidad,
    crear_unidad_administrativa,
    listar_unidades_administrativas,
    obtener_unidad_administrativa,
    revocar_usuario_unidad,
)


router = APIRouter(
    prefix="/admin/unidades",
    tags=["Gestión y seguimiento - Unidades"],
)


# ============================================================
# UNIDADES ADMINISTRATIVAS
# ============================================================


@router.get(
    "",
    response_model=ListaUnidadesResponse,
    status_code=status.HTTP_200_OK,
)
def listar_unidades(
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
    solo_activas: bool = Query(
        default=False,
    ),
    busqueda: str | None = Query(
        default=None,
        min_length=1,
        max_length=150,
    ),
) -> ListaUnidadesResponse:
    """
    Lista las unidades administrativas registradas.

    Solo puede utilizarlo un administrador.
    """
    return listar_unidades_administrativas(
        db,
        pagina=pagina,
        por_pagina=por_pagina,
        solo_activas=solo_activas,
        texto_busqueda=busqueda,
    )


@router.post(
    "",
    response_model=UnidadResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_unidad(
    datos: UnidadCrearRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> UnidadResponse:
    """
    Registra una nueva unidad administrativa.
    """
    try:
        return crear_unidad_administrativa(
            db,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except UnidadDuplicadaError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except UnidadServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{id_unidad}",
    response_model=UnidadDetalleResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_unidad(
    id_unidad: int,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> UnidadDetalleResponse:
    """
    Devuelve el detalle de una unidad administrativa.
    """
    try:
        return obtener_unidad_administrativa(
            db,
            id_unidad=id_unidad,
        )

    except UnidadNoEncontradaError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{id_unidad}",
    response_model=UnidadResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_unidad(
    id_unidad: int,
    datos: UnidadActualizarRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> UnidadResponse:
    """
    Modifica los datos o el estado de una unidad administrativa.
    """
    try:
        return actualizar_unidad_administrativa(
            db,
            id_unidad=id_unidad,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except UnidadNoEncontradaError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except UnidadDuplicadaError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ActualizacionUnidadVaciaError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except UnidadServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# ASOCIACIONES USUARIO ↔ UNIDAD
# ============================================================


@router.post(
    "/{id_unidad}/usuarios",
    response_model=UsuarioUnidadResponse,
    status_code=status.HTTP_201_CREATED,
)
def asignar_usuario(
    id_unidad: int,
    datos: UsuarioUnidadAsignarRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> UsuarioUnidadResponse:
    """
    Asocia un usuario con rol personal_administrativo
    a una unidad administrativa.
    """
    try:
        return asignar_usuario_unidad(
            db,
            id_unidad=id_unidad,
            id_usuario=datos.id_usuario,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except UnidadNoEncontradaError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except UsuarioNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except UsuarioUnidadYaAsignadaError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except UsuarioSinRolAdministrativoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except UnidadServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{id_unidad}/usuarios/{id_usuario}",
    response_model=UsuarioUnidadResponse,
    status_code=status.HTTP_200_OK,
)
def revocar_usuario(
    id_unidad: int,
    id_usuario: int,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> UsuarioUnidadResponse:
    """
    Revoca la asociación activa entre un usuario y una unidad.

    El registro no se elimina para conservar trazabilidad.
    """
    try:
        return revocar_usuario_unidad(
            db,
            id_unidad=id_unidad,
            id_usuario=id_usuario,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except UnidadNoEncontradaError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except UsuarioNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except UsuarioUnidadNoAsignadaError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except UnidadServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc