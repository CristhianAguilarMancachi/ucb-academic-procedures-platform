
from __future__ import annotations

from datetime import date

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
    status,
)

from pydantic import BaseModel
from sqlalchemy import select

from app.core.dependencies import (
    DatabaseSession,
    PersonalAdministrativoActual,
)

from app.models.gestion_seguimiento.unidad_administrativa import (
    UnidadAdministrativa,
)

from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoVerificacionResultadoResponse,
)

from app.schemas.gestion_seguimiento.solicitud_administrativa import (
    EstadoSolicitudAdministrativa,
    ListaSolicitudesAdministrativasResponse,
    RequisitoVerificacionResponse,
    RequisitoVerificarRequest,
    RequisitosAdministrativosConfirmarRequest,
    RequisitosAdministrativosConfirmarResponse,
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
    RequisitoAdministrativoYaConfirmadoError,
    RequisitoEconomicoRequiereApiError,
    RequisitoNoEsAdministrativoError,
    RequisitoNoPerteneceSolicitudError,
    RequisitoSolicitudNoEncontradoError,
    SolicitudAdministrativaNoEncontradaError,
    SolicitudNoEstaEnRevisionError,
    SolicitudNoPendienteRecepcionError,
    SolicitudYaRecibidaError,
    confirmar_requisitos_administrativos,
    listar_bandeja_administrativa,
    obtener_detalle_administrativo,
    recibir_solicitud,
    verificar_requisito_manual,
)


router = APIRouter(
    prefix="/admin/solicitudes",
    tags=["Administración de solicitudes"],
)


# ============================================================
# RESPUESTAS AUXILIARES
# ============================================================

class UnidadSubsanacionResponse(BaseModel):
    id_unidad: int
    nombre: str


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(
        exc,
        (
            SolicitudYaRecibidaError,
            SolicitudNoPendienteRecepcionError,
            SolicitudNoEstaEnRevisionError,
            SolicitudPagoNoEstaEnRevisionError,
            RequisitoEconomicoRequiereApiError,
            RequisitoNoEsAdministrativoError,
            RequisitoAdministrativoYaConfirmadoError,
            FacturaYaUtilizadaError,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if isinstance(
        exc,
        PagoApiNoDisponibleError,
    ):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=(
            "Ocurrió un error inesperado durante "
            "la gestión administrativa."
        ),
    )


# ============================================================
# CATÁLOGO DE UNIDADES PARA SUBSANACIÓN
# ============================================================

@router.get(
    "/unidades-subsanacion",
    response_model=list[UnidadSubsanacionResponse],
    status_code=status.HTTP_200_OK,
)
def consultar_unidades_para_subsanacion(
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> list[UnidadSubsanacionResponse]:
    """
    Catálogo de solo lectura para el formulario
    de observaciones administrativas.

    No concede permisos de administración de unidades.

    El canal de subsanación continúa guardándose como
    texto, por lo que también admite opciones manuales.
    """

    unidades = db.scalars(
        select(UnidadAdministrativa)
        .where(
            UnidadAdministrativa.activo.is_(True)
        )
        .order_by(
            UnidadAdministrativa.nombre.asc(),
            UnidadAdministrativa.id_unidad.asc(),
        )
    ).all()

    return [
        UnidadSubsanacionResponse(
            id_unidad=unidad.id_unidad,
            nombre=unidad.nombre,
        )
        for unidad in unidades
    ]


# ============================================================
# BANDEJA ADMINISTRATIVA
# ============================================================

@router.get(
    "",
    response_model=ListaSolicitudesAdministrativasResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_bandeja_solicitudes(
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
    estado: EstadoSolicitudAdministrativa | None = Query(
        default=None,
    ),
    id_tramite: int | None = Query(
        default=None,
        gt=0,
    ),
    id_solicitud: int | None = Query(
        default=None,
        gt=0,
    ),
    fecha_desde: date | None = Query(
        default=None,
    ),
    fecha_hasta: date | None = Query(
        default=None,
    ),
    id_solicitante: int | None = Query(
        default=None,
        gt=0,
    ),
    busqueda: str | None = Query(
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
    if (
        fecha_desde is not None
        and fecha_hasta is not None
        and fecha_desde > fecha_hasta
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rango de fechas no es válido.",
        )

    busqueda_normalizada = (
        busqueda.strip()
        if busqueda
        else None
    )

    if busqueda_normalizada == "":
        busqueda_normalizada = None

    return listar_bandeja_administrativa(
        db,
        estado=estado,
        id_tramite=id_tramite,
        id_solicitud=id_solicitud,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        id_solicitante=id_solicitante,
        busqueda=busqueda_normalizada,
        pagina=pagina,
        limite=limite,
    )


# ============================================================
# DETALLE ADMINISTRATIVO
# ============================================================

@router.get(
    "/{id_solicitud}",
    response_model=SolicitudAdministrativaDetalleResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_detalle_solicitud_administrativa(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> SolicitudAdministrativaDetalleResponse:
    try:
        return obtener_detalle_administrativo(
            db,
            id_solicitud=id_solicitud,
        )

    except SolicitudAdministrativaNoEncontradaError as exc:
        raise _error_administrativo(exc) from exc


# ============================================================
# RECEPCIÓN ADMINISTRATIVA
# ============================================================

@router.post(
    "/{id_solicitud}/recibir",
    response_model=SolicitudAdministrativaDetalleResponse,
    status_code=status.HTTP_200_OK,
)
def recibir_solicitud_administrativa(
    id_solicitud: int,
    request: Request,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> SolicitudAdministrativaDetalleResponse:
    try:
        return recibir_solicitud(
            db,
            id_solicitud=id_solicitud,
            id_usuario_receptor=usuario.id_usuario,
            direccion_ip=_obtener_direccion_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

    except (
        SolicitudAdministrativaNoEncontradaError,
        SolicitudYaRecibidaError,
        SolicitudNoPendienteRecepcionError,
    ) as exc:
        raise _error_administrativo(exc) from exc


# ============================================================
# CONFIRMACIÓN DE REQUISITOS ADMINISTRATIVOS
# ============================================================

@router.post(
    "/{id_solicitud}/requisitos/administrativos/confirmar",
    response_model=RequisitosAdministrativosConfirmarResponse,
    status_code=status.HTTP_200_OK,
)
def confirmar_requisitos_administrativos_solicitud(
    id_solicitud: int,
    datos: RequisitosAdministrativosConfirmarRequest,
    request: Request,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> RequisitosAdministrativosConfirmarResponse:
    try:
        return confirmar_requisitos_administrativos(
            db,
            id_solicitud=id_solicitud,
            id_usuario_verificador=usuario.id_usuario,
            datos=datos,
            direccion_ip=_obtener_direccion_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

    except (
        SolicitudAdministrativaNoEncontradaError,
        SolicitudNoEstaEnRevisionError,
        RequisitoNoPerteneceSolicitudError,
        RequisitoEconomicoRequiereApiError,
        RequisitoNoEsAdministrativoError,
        RequisitoAdministrativoYaConfirmadoError,
    ) as exc:
        raise _error_administrativo(exc) from exc


# ============================================================
# VERIFICACIÓN MANUAL EXISTENTE
# ============================================================

@router.post(
    "/{id_solicitud}/requisitos/{id_solicitud_requisito}/verificar",
    response_model=RequisitoVerificacionResponse,
    status_code=status.HTTP_200_OK,
)
def verificar_requisito_administrativamente(
    id_solicitud: int,
    id_solicitud_requisito: int,
    datos: RequisitoVerificarRequest,
    request: Request,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> RequisitoVerificacionResponse:
    try:
        return verificar_requisito_manual(
            db,
            id_solicitud=id_solicitud,
            id_solicitud_requisito=id_solicitud_requisito,
            id_usuario_verificador=usuario.id_usuario,
            datos=datos,
            direccion_ip=_obtener_direccion_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

    except (
        SolicitudAdministrativaNoEncontradaError,
        SolicitudNoEstaEnRevisionError,
        RequisitoSolicitudNoEncontradoError,
        RequisitoNoPerteneceSolicitudError,
        RequisitoEconomicoRequiereApiError,
        RequisitoNoEsAdministrativoError,
    ) as exc:
        raise _error_administrativo(exc) from exc


# ============================================================
# VERIFICACIÓN DE REQUISITOS ECONÓMICOS
# ============================================================

@router.post(
    "/{id_solicitud}/requisitos/{id_solicitud_requisito}/verificar-pago",
    response_model=PagoVerificacionResultadoResponse,
    status_code=status.HTTP_200_OK,
)
def verificar_pago_solicitud(
    id_solicitud: int,
    id_solicitud_requisito: int,
    request: Request,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
) -> PagoVerificacionResultadoResponse:
    try:
        return verificar_pago_requisito(
            db,
            id_solicitud=id_solicitud,
            id_solicitud_requisito=id_solicitud_requisito,
            id_usuario_verificador=usuario.id_usuario,
            direccion_ip=_obtener_direccion_ip(request),
            user_agent=request.headers.get("user-agent"),
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
        raise _error_administrativo(exc) from exc
