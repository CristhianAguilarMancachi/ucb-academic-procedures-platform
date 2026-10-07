from __future__ import annotations

from datetime import date

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
    status,
)

from app.core.dependencies import (
    DatabaseSession,
    PersonalAdministrativoActual,
)
from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoVerificacionResultadoResponse,
)
from app.schemas.gestion_seguimiento.solicitud_administrativa import (
    EstadoSolicitudAdministrativa,
    ListaSolicitudesAdministrativasResponse,
    RequisitoVerificacionResponse,
    RequisitoVerificarRequest,
    SolicitudAdministrativaDetalleResponse,
)
from app.services.gestion_seguimiento.pago_verificacion_service import (
    FacturaYaUtilizadaError,
    InformacionPagoIncompletaError,
    PagoApiNoDisponibleError,
    RequisitoNoEconomicoError,
    RequisitoNoPerteneceSolicitudPagoError,
    RequisitoPagoNoEncontradoError,
    SolicitudPagoNoEncontradaError,
    SolicitudPagoNoEstaEnRevisionError,
    verificar_pago_requisito,
)
from app.services.gestion_seguimiento.solicitud_administrativa_service import (
    RequisitoEconomicoRequiereApiError,
    RequisitoNoPerteneceSolicitudError,
    RequisitoSolicitudNoEncontradoError,
    SolicitudAdministrativaNoEncontradaError,
    SolicitudNoEstaEnRevisionError,
    SolicitudNoPendienteRecepcionError,
    SolicitudYaRecibidaError,
    listar_bandeja_administrativa,
    obtener_detalle_administrativo,
    recibir_solicitud,
    verificar_requisito_manual,
)


router = APIRouter(
    prefix="/admin/solicitudes",
    tags=[
        "Administración de solicitudes"
    ],
)


def _obtener_direccion_ip(
    request: Request,
) -> str | None:
    if request.client is None:
        return None

    return request.client.host


def _error_administrativo(
    exc: Exception,
) -> HTTPException:
    if isinstance(
        exc,
        (
            SolicitudAdministrativaNoEncontradaError,
            SolicitudPagoNoEncontradaError,
            RequisitoSolicitudNoEncontradoError,
            RequisitoPagoNoEncontradoError,
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
            SolicitudYaRecibidaError,
            SolicitudNoPendienteRecepcionError,
            SolicitudNoEstaEnRevisionError,
            SolicitudPagoNoEstaEnRevisionError,
            RequisitoEconomicoRequiereApiError,
            FacturaYaUtilizadaError,
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
            RequisitoNoPerteneceSolicitudError,
            RequisitoNoPerteneceSolicitudPagoError,
            RequisitoNoEconomicoError,
            InformacionPagoIncompletaError,
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

    if isinstance(
        exc,
        PagoApiNoDisponibleError,
    ):
        return HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(
                exc
            ),
        )

    return HTTPException(
        status_code=(
            status
            .HTTP_500_INTERNAL_SERVER_ERROR
        ),
        detail=(
            "Ocurrió un error inesperado durante "
            "la gestión administrativa."
        ),
    )


# ============================================================
# BANDEJA ADMINISTRATIVA
# ============================================================


@router.get(
    "",
    response_model=(
        ListaSolicitudesAdministrativasResponse
    ),
    status_code=(
        status.HTTP_200_OK
    ),
)
def consultar_bandeja_solicitudes(
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,

    estado: (
        EstadoSolicitudAdministrativa
        | None
    ) = Query(
        default=None,
    ),

    id_tramite: (
        int | None
    ) = Query(
        default=None,
        gt=0,
    ),

    id_solicitud: (
        int | None
    ) = Query(
        default=None,
        gt=0,
    ),

    fecha_desde: (
        date | None
    ) = Query(
        default=None,
    ),

    fecha_hasta: (
        date | None
    ) = Query(
        default=None,
    ),

    id_solicitante: (
        int | None
    ) = Query(
        default=None,
        gt=0,
    ),

    busqueda: (
        str | None
    ) = Query(
        default=None,
        min_length=1,
        max_length=200,
    ),

    pagina: int = Query(
        default=1,
        ge=1,
    ),

    limite: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> ListaSolicitudesAdministrativasResponse:
    """
    Lista solicitudes enviadas.

    La búsqueda general admite:
    - número de solicitud;
    - nombre o apellido;
    - documento de identidad / CI;
    - nombre del trámite.
    """
    if (
        fecha_desde
        and fecha_hasta
        and fecha_desde
        > fecha_hasta
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "El rango de fechas "
                "no es válido."
            ),
        )

    busqueda_normalizada = (
        busqueda.strip()
        if busqueda
        else None
    )

    if (
        busqueda_normalizada
        == ""
    ):
        busqueda_normalizada = None

    return (
        listar_bandeja_administrativa(
            db,

            estado=estado,

            id_tramite=(
                id_tramite
            ),

            id_solicitud=(
                id_solicitud
            ),

            fecha_desde=(
                fecha_desde
            ),

            fecha_hasta=(
                fecha_hasta
            ),

            id_solicitante=(
                id_solicitante
            ),

            busqueda=(
                busqueda_normalizada
            ),

            pagina=(
                pagina
            ),

            limite=(
                limite
            ),
        )
    )


# ============================================================
# DETALLE ADMINISTRATIVO
# ============================================================


@router.get(
    "/{id_solicitud}",
    response_model=(
        SolicitudAdministrativaDetalleResponse
    ),
    status_code=(
        status.HTTP_200_OK
    ),
)
def consultar_detalle_solicitud_administrativa(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> SolicitudAdministrativaDetalleResponse:
    """
    Consulta la solicitud, sus datos y sus requisitos
    desde la perspectiva administrativa.
    """
    try:
        return (
            obtener_detalle_administrativo(
                db,
                id_solicitud=(
                    id_solicitud
                ),
            )
        )

    except (
        SolicitudAdministrativaNoEncontradaError
    ) as exc:
        raise (
            _error_administrativo(
                exc
            )
        ) from exc


# ============================================================
# RECEPCIÓN ADMINISTRATIVA
# ============================================================


@router.post(
    "/{id_solicitud}/recibir",
    response_model=(
        SolicitudAdministrativaDetalleResponse
    ),
    status_code=(
        status.HTTP_200_OK
    ),
)
def recibir_solicitud_administrativa(
    id_solicitud: int,
    request: Request,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> SolicitudAdministrativaDetalleResponse:
    """
    Registra la recepción inicial.

    Transición:

        pendiente_recepcion
                ↓
            en_revision

    No asigna unidad ni ejecuta etapas.
    """
    try:
        return (
            recibir_solicitud(
                db,

                id_solicitud=(
                    id_solicitud
                ),

                id_usuario_receptor=(
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
        )

    except (
        SolicitudAdministrativaNoEncontradaError,
        SolicitudYaRecibidaError,
        SolicitudNoPendienteRecepcionError,
    ) as exc:
        raise (
            _error_administrativo(
                exc
            )
        ) from exc


# ============================================================
# REVISIÓN DE REQUISITOS NORMALES
# ============================================================


@router.post(
    (
        "/{id_solicitud}"
        "/requisitos"
        "/{id_solicitud_requisito}"
        "/verificar"
    ),
    response_model=(
        RequisitoVerificacionResponse
    ),
    status_code=(
        status.HTTP_200_OK
    ),
)
def verificar_requisito_administrativamente(
    id_solicitud: int,
    id_solicitud_requisito: int,
    datos: RequisitoVerificarRequest,
    request: Request,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> RequisitoVerificacionResponse:
    """
    Revisión manual de un requisito no económico.

    Un requisito económico no puede aprobarse
    desde este endpoint.
    """
    try:
        return (
            verificar_requisito_manual(
                db,

                id_solicitud=(
                    id_solicitud
                ),

                id_solicitud_requisito=(
                    id_solicitud_requisito
                ),

                id_usuario_verificador=(
                    usuario.id_usuario
                ),

                datos=(
                    datos
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
        )

    except (
        SolicitudAdministrativaNoEncontradaError,
        SolicitudNoEstaEnRevisionError,
        RequisitoSolicitudNoEncontradoError,
        RequisitoNoPerteneceSolicitudError,
        RequisitoEconomicoRequiereApiError,
    ) as exc:
        raise (
            _error_administrativo(
                exc
            )
        ) from exc


# ============================================================
# VERIFICACIÓN DE REQUISITOS ECONÓMICOS
# ============================================================


@router.post(
    (
        "/{id_solicitud}"
        "/requisitos"
        "/{id_solicitud_requisito}"
        "/verificar-pago"
    ),
    response_model=(
        PagoVerificacionResultadoResponse
    ),
    status_code=(
        status.HTTP_200_OK
    ),
)
def verificar_pago_solicitud(
    id_solicitud: int,
    id_solicitud_requisito: int,
    request: Request,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> PagoVerificacionResultadoResponse:
    """
    Verifica mediante API externa la factura asociada
    al requisito económico.

    El usuario administrativo NO introduce monto,
    moneda, código ni número de factura aquí.

    Esos valores provienen del snapshot de la solicitud.
    """
    try:
        return (
            verificar_pago_requisito(
                db,

                id_solicitud=(
                    id_solicitud
                ),

                id_solicitud_requisito=(
                    id_solicitud_requisito
                ),

                id_usuario_verificador=(
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
        )

    except (
        SolicitudPagoNoEncontradaError,
        SolicitudPagoNoEstaEnRevisionError,
        RequisitoPagoNoEncontradoError,
        RequisitoNoPerteneceSolicitudPagoError,
        RequisitoNoEconomicoError,
        InformacionPagoIncompletaError,
        FacturaYaUtilizadaError,
        PagoApiNoDisponibleError,
    ) as exc:
        raise (
            _error_administrativo(
                exc
            )
        ) from exc