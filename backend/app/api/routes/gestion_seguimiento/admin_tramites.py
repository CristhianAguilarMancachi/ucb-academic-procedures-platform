
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

from app.schemas.gestion_seguimiento.tramite import (
    ListaTramitesResponse,
    TramiteActualizarRequest,
    TramiteCrearRequest,
    TramiteDetalleResponse,
    TramiteResponse,
)

from app.schemas.gestion_seguimiento.tramite_campo import (
    TramiteCampoActualizarRequest,
    TramiteCampoCrearRequest,
    TramiteCampoResponse,
)

from app.schemas.gestion_seguimiento.tramite_requisito import (
    RequisitoEconomicoActualizarRequest,
    RequisitoEconomicoCrearRequest,
    RequisitoEconomicoResponse,
    TramiteRequisitoActualizarRequest,
    TramiteRequisitoCrearRequest,
    TramiteRequisitoResponse,
)

from app.services.gestion_seguimiento import (
    tramite_service as servicio,
)


router = APIRouter(
    prefix="/admin/tramites",
    tags=["Gestión y seguimiento - Trámites"],
)


# ============================================================
# ERRORES
# ============================================================

def _convertir_error_servicio(
    exc: servicio.TramiteServiceError,
) -> HTTPException:

    errores_no_encontrados = (
        servicio.TramiteNoEncontradoError,
        servicio.RequisitoNoEncontradoError,
        servicio.RequisitoNoPerteneceTramiteError,
        servicio.ConfiguracionEconomicaNoEncontradaError,
        servicio.CampoNoEncontradoError,
        servicio.CampoNoPerteneceTramiteError,
    )

    errores_conflicto = (
        servicio.TramiteDuplicadoError,
        servicio.RequisitoDuplicadoError,
        servicio.ConfiguracionEconomicaDuplicadaError,
        servicio.CampoDuplicadoError,
    )

    if isinstance(exc, errores_no_encontrados):
        codigo = status.HTTP_404_NOT_FOUND

    elif isinstance(exc, errores_conflicto):
        codigo = status.HTTP_409_CONFLICT

    else:
        codigo = status.HTTP_400_BAD_REQUEST

    return HTTPException(
        status_code=codigo,
        detail=str(exc),
    )


def _ejecutar(operacion, *args, **kwargs):
    try:
        return operacion(*args, **kwargs)

    except servicio.TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


def _auditoria(request: Request) -> dict:
    return {
        "direccion_ip": obtener_direccion_ip(request),
        "user_agent": obtener_user_agent(request),
    }


# ============================================================
# TRÁMITES
# ============================================================

@router.get(
    "",
    response_model=ListaTramitesResponse,
    status_code=status.HTTP_200_OK,
)
def listar_tramites(
    administrador: AdministradorActual,
    db: DatabaseSession,
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
    activo: bool | None = Query(default=None),
    publicado: bool | None = Query(default=None),
    permite_solicitudes: bool | None = Query(default=None),
    busqueda: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
    ),
) -> ListaTramitesResponse:

    return _ejecutar(
        servicio.listar_tramites_administracion,
        db,
        pagina=pagina,
        por_pagina=por_pagina,
        activo=activo,
        publicado=publicado,
        permite_solicitudes=permite_solicitudes,
        texto_busqueda=busqueda,
    )


@router.post(
    "",
    response_model=TramiteResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_tramite(
    datos: TramiteCrearRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> TramiteResponse:

    return _ejecutar(
        servicio.crear_tramite_catalogo,
        db,
        datos=datos,
        id_usuario_actor=administrador.id_usuario,
        **_auditoria(request),
    )


@router.get(
    "/{id_tramite}",
    response_model=TramiteDetalleResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_tramite(
    id_tramite: int,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> TramiteDetalleResponse:

    return _ejecutar(
        servicio.obtener_tramite_administracion,
        db,
        id_tramite=id_tramite,
    )


@router.patch(
    "/{id_tramite}",
    response_model=TramiteResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_tramite(
    id_tramite: int,
    datos: TramiteActualizarRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> TramiteResponse:

    return _ejecutar(
        servicio.actualizar_tramite_catalogo,
        db,
        id_tramite=id_tramite,
        datos=datos,
        id_usuario_actor=administrador.id_usuario,
        **_auditoria(request),
    )


# ============================================================
# REQUISITOS
# ============================================================

@router.post(
    "/{id_tramite}/requisitos",
    response_model=TramiteRequisitoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_requisito(
    id_tramite: int,
    datos: TramiteRequisitoCrearRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> TramiteRequisitoResponse:

    return _ejecutar(
        servicio.agregar_requisito_tramite,
        db,
        id_tramite=id_tramite,
        datos=datos,
        id_usuario_actor=administrador.id_usuario,
        **_auditoria(request),
    )


@router.patch(
    "/{id_tramite}/requisitos/{id_requisito}",
    response_model=TramiteRequisitoResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_requisito(
    id_tramite: int,
    id_requisito: int,
    datos: TramiteRequisitoActualizarRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> TramiteRequisitoResponse:

    return _ejecutar(
        servicio.actualizar_requisito_tramite,
        db,
        id_tramite=id_tramite,
        id_requisito=id_requisito,
        datos=datos,
        id_usuario_actor=administrador.id_usuario,
        **_auditoria(request),
    )


# ============================================================
# CONFIGURACIONES ECONÓMICAS
# ============================================================

@router.post(
    (
        "/{id_tramite}/requisitos/{id_requisito}"
        "/configuraciones-economicas"
    ),
    response_model=RequisitoEconomicoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_configuracion_economica(
    id_tramite: int,
    id_requisito: int,
    datos: RequisitoEconomicoCrearRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> RequisitoEconomicoResponse:

    return _ejecutar(
        servicio.agregar_configuracion_economica,
        db,
        id_tramite=id_tramite,
        id_requisito=id_requisito,
        datos=datos,
        id_usuario_actor=administrador.id_usuario,
        **_auditoria(request),
    )


@router.patch(
    (
        "/{id_tramite}/requisitos/{id_requisito}"
        "/configuraciones-economicas/{id_requisito_economico}"
    ),
    response_model=RequisitoEconomicoResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_configuracion_economica(
    id_tramite: int,
    id_requisito: int,
    id_requisito_economico: int,
    datos: RequisitoEconomicoActualizarRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> RequisitoEconomicoResponse:

    return _ejecutar(
        servicio.actualizar_configuracion_economica_tramite,
        db,
        id_tramite=id_tramite,
        id_requisito=id_requisito,
        id_requisito_economico=id_requisito_economico,
        datos=datos,
        id_usuario_actor=administrador.id_usuario,
        **_auditoria(request),
    )


# ============================================================
# CAMPOS CONFIGURABLES
# ============================================================

@router.post(
    "/{id_tramite}/campos",
    response_model=TramiteCampoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_campo(
    id_tramite: int,
    datos: TramiteCampoCrearRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> TramiteCampoResponse:

    return _ejecutar(
        servicio.agregar_campo_tramite,
        db,
        id_tramite=id_tramite,
        datos=datos,
        id_usuario_actor=administrador.id_usuario,
        **_auditoria(request),
    )


@router.patch(
    "/{id_tramite}/campos/{id_campo}",
    response_model=TramiteCampoResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_campo(
    id_tramite: int,
    id_campo: int,
    datos: TramiteCampoActualizarRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> TramiteCampoResponse:

    return _ejecutar(
        servicio.actualizar_campo_tramite,
        db,
        id_tramite=id_tramite,
        id_campo=id_campo,
        datos=datos,
        id_usuario_actor=administrador.id_usuario,
        **_auditoria(request),
    )
