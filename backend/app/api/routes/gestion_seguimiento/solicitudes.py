from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from app.core.dependencies import (
    DatabaseSession,
    SolicitanteActual,
)
from app.schemas.gestion_seguimiento.solicitud import (
    EstadoSolicitud,
    ListaSolicitudesResponse,
    SolicitudActualizarRequest,
    SolicitudCrearRequest,
    SolicitudEnviarRequest,
    SolicitudResponse,
)
from app.services.gestion_seguimiento.solicitud_service import (
    ActualizacionSolicitudVaciaError,
    CampoSolicitudInvalidoError,
    CamposObligatoriosFaltantesError,
    ConfiguracionCampoInvalidaError,
    ConfiguracionEconomicaIncompletaError,
    FacturaSolicitudInvalidaError,
    SolicitudInconsistenteError,
    SolicitudNoEncontradaError,
    SolicitudNoEsBorradorError,
    TramiteNoDisponibleParaSolicitudError,
    TramiteSolicitudNoEncontradoError,
    ValorCampoInvalidoError,
    actualizar_solicitud,
    crear_solicitud,
    eliminar_solicitud,
    enviar_solicitud,
    listar_mis_solicitudes,
    obtener_solicitud,
)


router = APIRouter(
    prefix="/solicitudes",
    tags=["Solicitudes"],
)


def _obtener_direccion_ip(
    request: Request,
) -> str | None:
    if request.client is None:
        return None

    return request.client.host


def _convertir_error_servicio(
    exc: Exception,
) -> HTTPException:
    if isinstance(
        exc,
        (
            SolicitudNoEncontradaError,
            TramiteSolicitudNoEncontradoError,
        ),
    ):
        return HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(
                exc
            ),
        )

    if isinstance(
        exc,
        (
            SolicitudNoEsBorradorError,
            TramiteNoDisponibleParaSolicitudError,
            ConfiguracionEconomicaIncompletaError,
            SolicitudInconsistenteError,
        ),
    ):
        return HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(
                exc
            ),
        )

    if isinstance(
        exc,
        (
            ActualizacionSolicitudVaciaError,
            CampoSolicitudInvalidoError,
            ValorCampoInvalidoError,
            ConfiguracionCampoInvalidaError,
            CamposObligatoriosFaltantesError,
            FacturaSolicitudInvalidaError,
        ),
    ):
        return HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(
                exc
            ),
        )

    return HTTPException(
        status_code=(
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        detail=(
            "Ocurrió un error inesperado "
            "al procesar la solicitud."
        ),
    )


# ============================================================
# CREAR BORRADOR
# ============================================================


@router.post(
    "",
    response_model=SolicitudResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def crear_borrador_solicitud(
    datos: SolicitudCrearRequest,
    request: Request,
    db: DatabaseSession,
    usuario: SolicitanteActual,
) -> SolicitudResponse:
    """
    Crea una nueva solicitud en estado borrador.
    """
    try:
        return crear_solicitud(
            db,
            id_solicitante=(
                usuario.id_usuario
            ),
            datos=datos,
            direccion_ip=(
                _obtener_direccion_ip(
                    request
                )
            ),
            user_agent=(
                request.headers.get(
                    "user-agent"
                )
            ),
        )

    except Exception as exc:
        if isinstance(
            exc,
            (
                TramiteSolicitudNoEncontradoError,
                TramiteNoDisponibleParaSolicitudError,
            ),
        ):
            raise (
                _convertir_error_servicio(
                    exc
                )
            ) from exc

        raise


# ============================================================
# LISTAR MIS SOLICITUDES
# ============================================================


@router.get(
    "/mias",
    response_model=(
        ListaSolicitudesResponse
    ),
    status_code=(
        status.HTTP_200_OK
    ),
)
def consultar_mis_solicitudes(
    db: DatabaseSession,
    usuario: SolicitanteActual,
    estado: EstadoSolicitud | None = Query(
        default=None,
    ),
    pagina: int = Query(
        default=1,
        ge=1,
    ),
    por_pagina: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> ListaSolicitudesResponse:
    """
    Lista únicamente las solicitudes
    pertenecientes al usuario autenticado.
    """
    return listar_mis_solicitudes(
        db,
        id_solicitante=(
            usuario.id_usuario
        ),
        estado=estado,
        pagina=pagina,
        por_pagina=por_pagina,
    )


# ============================================================
# CONSULTAR SOLICITUD
# ============================================================


@router.get(
    "/{id_solicitud}",
    response_model=SolicitudResponse,
    status_code=(
        status.HTTP_200_OK
    ),
)
def consultar_solicitud(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: SolicitanteActual,
) -> SolicitudResponse:
    """
    Obtiene una solicitud propia.
    """
    try:
        return obtener_solicitud(
            db,
            id_solicitud=id_solicitud,
            id_solicitante=(
                usuario.id_usuario
            ),
        )

    except (
        SolicitudNoEncontradaError
    ) as exc:
        raise (
            _convertir_error_servicio(
                exc
            )
        ) from exc


# ============================================================
# ACTUALIZAR BORRADOR
# ============================================================


@router.patch(
    "/{id_solicitud}",
    response_model=SolicitudResponse,
    status_code=(
        status.HTTP_200_OK
    ),
)
def actualizar_borrador_solicitud(
    id_solicitud: int,
    datos: SolicitudActualizarRequest,
    request: Request,
    db: DatabaseSession,
    usuario: SolicitanteActual,
) -> SolicitudResponse:
    """
    Actualiza los datos dinámicos de una solicitud
    mientras permanezca en borrador.
    """
    try:
        return actualizar_solicitud(
            db,
            id_solicitud=id_solicitud,
            id_solicitante=(
                usuario.id_usuario
            ),
            datos=datos,
            direccion_ip=(
                _obtener_direccion_ip(
                    request
                )
            ),
            user_agent=(
                request.headers.get(
                    "user-agent"
                )
            ),
        )

    except (
        SolicitudNoEncontradaError,
        SolicitudNoEsBorradorError,
        ActualizacionSolicitudVaciaError,
        CampoSolicitudInvalidoError,
        ValorCampoInvalidoError,
        ConfiguracionCampoInvalidaError,
    ) as exc:
        raise (
            _convertir_error_servicio(
                exc
            )
        ) from exc


# ============================================================
# ELIMINAR BORRADOR
# ============================================================


@router.delete(
    "/{id_solicitud}",
    status_code=(
        status.HTTP_204_NO_CONTENT
    ),
)
def eliminar_borrador_solicitud(
    id_solicitud: int,
    request: Request,
    db: DatabaseSession,
    usuario: SolicitanteActual,
) -> Response:
    """
    Elimina una solicitud propia únicamente
    mientras permanezca en borrador.
    """
    try:
        eliminar_solicitud(
            db,
            id_solicitud=id_solicitud,
            id_solicitante=(
                usuario.id_usuario
            ),
            direccion_ip=(
                _obtener_direccion_ip(
                    request
                )
            ),
            user_agent=(
                request.headers.get(
                    "user-agent"
                )
            ),
        )

        return Response(
            status_code=(
                status.HTTP_204_NO_CONTENT
            )
        )

    except (
        SolicitudNoEncontradaError,
        SolicitudNoEsBorradorError,
    ) as exc:
        raise (
            _convertir_error_servicio(
                exc
            )
        ) from exc


# ============================================================
# ENVIAR SOLICITUD
# ============================================================


@router.post(
    "/{id_solicitud}/enviar",
    response_model=SolicitudResponse,
    status_code=(
        status.HTTP_200_OK
    ),
)
def enviar_borrador_solicitud(
    id_solicitud: int,
    datos: SolicitudEnviarRequest,
    request: Request,
    db: DatabaseSession,
    usuario: SolicitanteActual,
) -> SolicitudResponse:
    """
    Registra formalmente una solicitud en borrador.

    El body se conserva temporalmente para compatibilidad
    con el cliente actual, pero la operación de envío NO
    procesa información de pago ni declaraciones físicas.

    Pago y documentación se gestionan posteriormente desde
    el seguimiento de la solicitud.
    """
    # El modelo de entrada está intencionalmente vacío.
    #
    # Una versión anterior del frontend puede seguir enviando
    # propiedades de facturas o entrega física. El schema las
    # ignora y nunca llegan a la lógica de negocio.
    _ = datos

    try:
        return enviar_solicitud(
            db,
            id_solicitud=id_solicitud,
            id_solicitante=(
                usuario.id_usuario
            ),
            direccion_ip=(
                _obtener_direccion_ip(
                    request
                )
            ),
            user_agent=(
                request.headers.get(
                    "user-agent"
                )
            ),
        )

    except (
        SolicitudNoEncontradaError,
        SolicitudNoEsBorradorError,
        TramiteSolicitudNoEncontradoError,
        TramiteNoDisponibleParaSolicitudError,
        ValorCampoInvalidoError,
        ConfiguracionCampoInvalidaError,
        CamposObligatoriosFaltantesError,
        ConfiguracionEconomicaIncompletaError,
        SolicitudInconsistenteError,
    ) as exc:
        raise (
            _convertir_error_servicio(
                exc
            )
        ) from exc