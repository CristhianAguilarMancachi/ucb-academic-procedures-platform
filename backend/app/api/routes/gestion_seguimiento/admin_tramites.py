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
from app.schemas.gestion_seguimiento.tramite_etapa import (
    TramiteEtapaActualizarRequest,
    TramiteEtapaCrearRequest,
    TramiteEtapaResponse,
    EtapasOrdenRequest,
)
from app.schemas.gestion_seguimiento.tramite_requisito import (
    RequisitoEconomicoActualizarRequest,
    RequisitoEconomicoCrearRequest,
    RequisitoEconomicoResponse,
    TramiteRequisitoActualizarRequest,
    TramiteRequisitoCrearRequest,
    TramiteRequisitoResponse,
)
from app.services.gestion_seguimiento.tramite_service import (
    ActualizacionTramiteVaciaError,
    CampoDuplicadoError,
    CampoNoEncontradoError,
    CampoNoPerteneceTramiteError,
    ConfiguracionEconomicaDuplicadaError,
    ConfiguracionEconomicaNoEncontradaError,
    ConfiguracionTramiteInvalidaError,
    EtapaDuplicadaError,
    EtapaNoEncontradaError,
    EtapaNoPerteneceTramiteError,
    RequisitoDuplicadoError,
    RequisitoNoEncontradoError,
    RequisitoNoPerteneceTramiteError,
    TramiteDuplicadoError,
    TramiteNoEncontradoError,
    TramiteServiceError,
    UnidadInactivaError,
    UnidadNoEncontradaError,
    actualizar_campo_tramite,
    actualizar_configuracion_economica_tramite,
    actualizar_etapa_tramite,
    reordenar_etapas,
    actualizar_requisito_tramite,
    actualizar_tramite_catalogo,
    agregar_campo_tramite,
    agregar_configuracion_economica,
    agregar_etapa_tramite,
    agregar_requisito_tramite,
    crear_tramite_catalogo,
    listar_tramites_administracion,
    obtener_tramite_administracion,
)


router = APIRouter(
    prefix="/admin/tramites",
    tags=["Gestión y seguimiento - Trámites"],
)


# ============================================================
# MANEJO DE ERRORES DEL SERVICIO
# ============================================================


def _convertir_error_servicio(
    exc: TramiteServiceError,
) -> HTTPException:
    """
    Convierte errores de negocio del catálogo en respuestas HTTP.
    """
    errores_no_encontrados = (
        TramiteNoEncontradoError,
        RequisitoNoEncontradoError,
        RequisitoNoPerteneceTramiteError,
        ConfiguracionEconomicaNoEncontradaError,
        CampoNoEncontradoError,
        CampoNoPerteneceTramiteError,
        EtapaNoEncontradaError,
        EtapaNoPerteneceTramiteError,
        UnidadNoEncontradaError,
    )

    errores_conflicto = (
        TramiteDuplicadoError,
        RequisitoDuplicadoError,
        ConfiguracionEconomicaDuplicadaError,
        CampoDuplicadoError,
        EtapaDuplicadaError,
    )

    if isinstance(exc, errores_no_encontrados):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, errores_conflicto):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


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
    pagina: int = Query(
        default=1,
        ge=1,
    ),
    por_pagina: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    activo: bool | None = Query(
        default=None,
    ),
    publicado: bool | None = Query(
        default=None,
    ),
    permite_solicitudes: bool | None = Query(
        default=None,
    ),
    busqueda: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
    ),
) -> ListaTramitesResponse:
    """
    Lista los trámites registrados con filtros administrativos.
    """
    return listar_tramites_administracion(
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
    """
    Registra un trámite dentro del catálogo administrativo.
    """
    try:
        return crear_tramite_catalogo(
            db,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


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
    """
    Devuelve la configuración completa de un trámite.

    Las etapas pueden estar vacías mientras el proceso
    institucional no haya sido confirmado.
    """
    try:
        return obtener_tramite_administracion(
            db,
            id_tramite=id_tramite,
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


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
    """
    Modifica la configuración general de un trámite.
    """
    try:
        return actualizar_tramite_catalogo(
            db,
            id_tramite=id_tramite,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


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
    """
    Agrega un requisito confirmado a un trámite.
    """
    try:
        return agregar_requisito_tramite(
            db,
            id_tramite=id_tramite,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


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
    """
    Modifica un requisito perteneciente al trámite.
    """
    try:
        return actualizar_requisito_tramite(
            db,
            id_tramite=id_tramite,
            id_requisito=id_requisito,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


# ============================================================
# CONFIGURACIÓN ECONÓMICA
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
    """
    Registra la información económica correspondiente
    a una gestión determinada.
    """
    try:
        return agregar_configuracion_economica(
            db,
            id_tramite=id_tramite,
            id_requisito=id_requisito,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


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
    """
    Actualiza una configuración económica existente.
    """
    try:
        return actualizar_configuracion_economica_tramite(
            db,
            id_tramite=id_tramite,
            id_requisito=id_requisito,
            id_requisito_economico=id_requisito_economico,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


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
    """
    Agrega un campo configurable a un trámite.
    """
    try:
        return agregar_campo_tramite(
            db,
            id_tramite=id_tramite,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


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
    """
    Modifica un campo configurable de un trámite.
    """
    try:
        return actualizar_campo_tramite(
            db,
            id_tramite=id_tramite,
            id_campo=id_campo,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


# ============================================================
# ETAPAS CONFIGURABLES
# ============================================================


@router.post(
    "/{id_tramite}/etapas",
    response_model=TramiteEtapaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_etapa(
    id_tramite: int,
    datos: TramiteEtapaCrearRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> TramiteEtapaResponse:
    """
    Registra una etapa únicamente cuando exista información
    institucional confirmada.

    El backend no deduce ni genera procesos automáticamente.
    """
    try:
        return agregar_etapa_tramite(
            db,
            id_tramite=id_tramite,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc


@router.patch(
    "/{id_tramite}/etapas/{id_etapa}",
    response_model=TramiteEtapaResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_etapa(
    id_tramite: int,
    id_etapa: int,
    datos: TramiteEtapaActualizarRequest,
    request: Request,
    administrador: AdministradorActual,
    db: DatabaseSession,
) -> TramiteEtapaResponse:
    """
    Modifica una etapa previamente configurada.
    """
    try:
        return actualizar_etapa_tramite(
            db,
            id_tramite=id_tramite,
            id_etapa=id_etapa,
            datos=datos,
            id_usuario_actor=administrador.id_usuario,
            direccion_ip=obtener_direccion_ip(request),
            user_agent=obtener_user_agent(request),
        )

    except TramiteServiceError as exc:
        raise _convertir_error_servicio(exc) from exc

@router.post("/{id_tramite}/etapas/orden", response_model=TramiteDetalleResponse)
def ordenar_etapas(id_tramite: int, datos: EtapasOrdenRequest, administrador: AdministradorActual, db: DatabaseSession):
    try:
        return reordenar_etapas(db, id_tramite=id_tramite, ids=datos.ids, id_usuario_actor=administrador.id_usuario)
    except TramiteNoEncontradoError as exc:
        raise HTTPException(404, str(exc)) from exc
    except TramiteServiceError as exc:
        raise HTTPException(400, str(exc)) from exc
