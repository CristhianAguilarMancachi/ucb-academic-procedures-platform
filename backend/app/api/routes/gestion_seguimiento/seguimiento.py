# RETIRO_ENTREGA_FISICA_13F

from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
)

from app.core.dependencies import (
    DatabaseSession,
    PersonalAdministrativoActual,
    SolicitanteActual,
)

from app.api.routes.gestion_seguimiento.solicitudes import (
    _convertir_error_servicio,
)

from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoVerificacionResultadoResponse,
)

from app.schemas.gestion_seguimiento.seguimiento import (
    FacturaRegistrarRequest,
    HistorialResponse,
    MotivoRequest,
    ObservacionCrearRequest,
    ObservacionPublicaResponse,
    ResultadoRegistrarRequest,
    SeguimientoResponse,
)

from app.schemas.gestion_seguimiento.solicitud import (
    SolicitudResponse,
)

from app.schemas.gestion_seguimiento.solicitud_administrativa import (
    SolicitudAdministrativaDetalleResponse,
)

from app.schemas.gestion_seguimiento.tramite import (
    TramiteCatalogoDetalleResponse,
)

from app.services.gestion_seguimiento import (
    atencion_service,
    pago_verificacion_service as pago_servicio,
    seguimiento_service as servicio,
    solicitud_service,
)

from app.services.gestion_seguimiento.notificacion_solicitud_service import (
    notificar_resultado_solicitud,
)

from app.services.gestion_seguimiento.solicitud_administrativa_service import (
    SolicitudAdministrativaNoEncontradaError,
    obtener_detalle_administrativo,
)

from app.services.gestion_seguimiento.tramite_service import (
    TramiteNoEncontradoError,
)


router = APIRouter(
    tags=["Seguimiento de solicitudes"],
)


def _direccion_ip(
    request: Request,
) -> str | None:
    return (
        request.client.host
        if request.client
        else None
    )


def _convertir_error_pago(
    exc: Exception,
) -> HTTPException:
    if isinstance(
        exc,
        (
            pago_servicio.SolicitudPagoNoEncontradaError,
            pago_servicio.RequisitoPagoNoEncontradoError,
            pago_servicio.RequisitoNoPerteneceSolicitudPagoError,
        ),
    ):
        codigo = status.HTTP_404_NOT_FOUND

    elif isinstance(
        exc,
        (
            pago_servicio.RequisitoNoEconomicoError,
            pago_servicio.InformacionPagoIncompletaError,
        ),
    ):
        codigo = status.HTTP_400_BAD_REQUEST

    elif isinstance(
        exc,
        (
            pago_servicio.SolicitudPagoNoEstaEnRevisionError,
            pago_servicio.FacturaYaUtilizadaError,
        ),
    ):
        codigo = status.HTTP_409_CONFLICT

    elif isinstance(
        exc,
        pago_servicio.PagoApiNoDisponibleError,
    ):
        codigo = status.HTTP_503_SERVICE_UNAVAILABLE

    else:
        return HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Ocurrió un error inesperado "
                "al verificar el pago."
            ),
        )

    return HTTPException(
        status_code=codigo,
        detail=str(exc),
    )


# ============================================================
# PREPARACIÓN Y SEGUIMIENTO DEL SOLICITANTE
# ============================================================

@router.get(
    "/solicitudes/{id_solicitud}/preparacion",
    response_model=TramiteCatalogoDetalleResponse,
)
def preparacion(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: SolicitanteActual,
):
    try:
        return solicitud_service.consultar_preparacion(
            db,
            id_solicitud,
            usuario.id_usuario,
        )

    except solicitud_service.SolicitudServiceError as exc:
        raise _convertir_error_servicio(
            exc
        ) from exc

    except TramiteNoEncontradoError as exc:
        raise servicio.SeguimientoError(
            str(exc),
            404,
        ) from exc


@router.get(
    "/solicitudes/{id_solicitud}/seguimiento",
    response_model=SeguimientoResponse,
)
def seguimiento(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: SolicitanteActual,
):
    return servicio.consultar_seguimiento(
        db,
        id_solicitud,
        usuario.id_usuario,
    )


@router.get(
    "/solicitudes/{id_solicitud}/observaciones",
    response_model=list[ObservacionPublicaResponse],
)
def observaciones(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: SolicitanteActual,
):
    return servicio.consultar_seguimiento(
        db,
        id_solicitud,
        usuario.id_usuario,
    ).observaciones


@router.post(
    "/solicitudes/{id_solicitud}/cancelar",
    response_model=SeguimientoResponse,
)
def cancelar(
    id_solicitud: int,
    datos: MotivoRequest,
    db: DatabaseSession,
    usuario: SolicitanteActual,
):
    servicio.cancelar(
        db,
        id_solicitud,
        usuario.id_usuario,
        datos.motivo,
    )

    return servicio.consultar_seguimiento(
        db,
        id_solicitud,
        usuario.id_usuario,
    )


# ============================================================
# FACTURACIÓN Y REQUISITOS DEL SOLICITANTE
# ============================================================

@router.put(
    "/solicitudes/{id_solicitud}/requisitos/{id_requisito}/factura",
    response_model=SolicitudResponse,
)
def registrar_factura(
    id_solicitud: int,
    id_requisito: int,
    datos: FacturaRegistrarRequest,
    db: DatabaseSession,
    usuario: SolicitanteActual,
):
    servicio.registrar_factura(
        db,
        id_solicitud,
        id_requisito,
        usuario.id_usuario,
        datos.numero_factura,
    )

    return solicitud_service.obtener_solicitud(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=usuario.id_usuario,
    )


@router.post(
    "/solicitudes/{id_solicitud}/requisitos/{id_requisito}/verificar-pago",
    response_model=PagoVerificacionResultadoResponse,
)
def verificar_pago_solicitante(
    id_solicitud: int,
    id_requisito: int,
    request: Request,
    db: DatabaseSession,
    usuario: SolicitanteActual,
) -> PagoVerificacionResultadoResponse:
    try:
        return pago_servicio.verificar_pago_solicitante(
            db,
            id_solicitud=id_solicitud,
            id_solicitud_requisito=id_requisito,
            id_solicitante=usuario.id_usuario,
            direccion_ip=_direccion_ip(
                request
            ),
            user_agent=request.headers.get(
                "user-agent"
            ),
        )

    except pago_servicio.PagoVerificacionServiceError as exc:
        raise _convertir_error_pago(
            exc
        ) from exc


@router.post(
    "/solicitudes/{id_solicitud}/requisitos/{id_requisito}/declaracion-fisica",
    response_model=SolicitudResponse,
)
def declarar_entrega_fisica(
    id_solicitud: int,
    id_requisito: int,
    db: DatabaseSession,
    usuario: SolicitanteActual,
):
    servicio.declarar_entrega_fisica(
        db,
        id_solicitud,
        id_requisito,
        usuario.id_usuario,
    )

    return solicitud_service.obtener_solicitud(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=usuario.id_usuario,
    )


# ============================================================
# CONSULTAS ADMINISTRATIVAS
# ============================================================

@router.get(
    "/admin/solicitudes/{id_solicitud}/historial",
    response_model=list[HistorialResponse],
)
def historial(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    try:
        return obtener_detalle_administrativo(
            db,
            id_solicitud=id_solicitud,
        ).historial

    except SolicitudAdministrativaNoEncontradaError as exc:
        raise servicio.SeguimientoError(
            str(exc),
            404,
        ) from exc


# ============================================================
# INICIAR ATENCIÓN
# ============================================================

@router.post(
    "/admin/solicitudes/{id_solicitud}/iniciar",
    response_model=SolicitudAdministrativaDetalleResponse,
)
def iniciar_procesamiento(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    atencion_service.iniciar_atencion(
        db,
        id_solicitud,
        usuario.id_usuario,
    )

    return obtener_detalle_administrativo(
        db,
        id_solicitud=id_solicitud,
    )


# ============================================================
# PRESENTACIÓN FÍSICA
# ============================================================

@router.post(
    "/admin/solicitudes/{id_solicitud}/requisitos/{id_requisito}/presentacion",
    response_model=SolicitudAdministrativaDetalleResponse,
)
def registrar_presentacion(
    id_solicitud: int,
    id_requisito: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    servicio.registrar_presentacion(
        db,
        id_solicitud,
        id_requisito,
        usuario.id_usuario,
    )

    return obtener_detalle_administrativo(
        db,
        id_solicitud=id_solicitud,
    )


# ============================================================
# OBSERVACIONES
# ============================================================

@router.post(
    "/admin/solicitudes/{id_solicitud}/observaciones",
    response_model=SolicitudAdministrativaDetalleResponse,
)
def crear_observacion(
    id_solicitud: int,
    datos: ObservacionCrearRequest,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    servicio.crear_observacion(
        db,
        id_solicitud,
        usuario.id_usuario,
        datos,
    )

    return obtener_detalle_administrativo(
        db,
        id_solicitud=id_solicitud,
    )


@router.post(
    "/admin/solicitudes/{id_solicitud}/observaciones/{id_observacion}/resolver",
    response_model=SolicitudAdministrativaDetalleResponse,
)
def resolver_observacion(
    id_solicitud: int,
    id_observacion: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    servicio.resolver_observacion(
        db,
        id_solicitud,
        id_observacion,
        usuario.id_usuario,
    )

    return obtener_detalle_administrativo(
        db,
        id_solicitud=id_solicitud,
    )


# ============================================================
# RECHAZO
# ============================================================

@router.post(
    "/admin/solicitudes/{id_solicitud}/rechazar",
    response_model=SolicitudAdministrativaDetalleResponse,
)
def rechazar(
    id_solicitud: int,
    datos: MotivoRequest,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    servicio.rechazar(
        db,
        id_solicitud,
        usuario.id_usuario,
        datos.motivo,
    )

    return obtener_detalle_administrativo(
        db,
        id_solicitud=id_solicitud,
    )


# ============================================================
# REGISTRAR RESULTADO
# ============================================================

@router.post(
    "/admin/solicitudes/{id_solicitud}/finalizar",
    response_model=SolicitudAdministrativaDetalleResponse,
)
def registrar_resultado(
    id_solicitud: int,
    datos: ResultadoRegistrarRequest,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    atencion_service.registrar_resultado(
        db,
        id_solicitud,
        usuario.id_usuario,
        datos,
    )

    # El correo se envía después de confirmar
    # el resultado en la base de datos.
    notificar_resultado_solicitud(
        db,
        id_solicitud,
    )

    return obtener_detalle_administrativo(
        db,
        id_solicitud=id_solicitud,
    )


# ============================================================
# ENTREGA FINAL
# ============================================================

