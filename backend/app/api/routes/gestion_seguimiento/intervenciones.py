
from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import (
    DatabaseSession,
    PersonalAdministrativoActual,
)

from app.repositories.gestion_seguimiento import (
    intervencion_repository as intervenciones,
    notificacion_repository as notificaciones,
    seguimiento_repository as seguimiento_repo,
)

from app.schemas.gestion_seguimiento.intervencion import (
    ConvocatoriaResponse,
    IntervencionResponse,
    ResolucionEmitidaResponse,
    RevisionPresencialRequest,
)

from app.schemas.gestion_seguimiento.notificacion import (
    NotificacionResponse,
)

from app.services.gestion_seguimiento import (
    intervencion_service,
    notificacion_solicitud_service,
)

from app.services.gestion_seguimiento.seguimiento_service import (
    SeguimientoError,
)


router = APIRouter(
    prefix="/admin/solicitudes",
    tags=["Intervenciones administrativas"],
)


def _exigir_solicitud(
    db: DatabaseSession,
    id_solicitud: int,
):
    solicitud = seguimiento_repo.obtener_solicitud_completa(
        db,
        id_solicitud,
    )

    if (
        solicitud is None
        or solicitud.estado == "borrador"
    ):
        raise SeguimientoError(
            "La solicitud no existe o no está "
            "disponible para gestión administrativa.",
            404,
        )

    return solicitud


# ============================================================
# RESOLUCIÓN INSTITUCIONAL
# ============================================================

@router.get(
    "/{id_solicitud}/resolucion",
    response_model=ResolucionEmitidaResponse | None,
)
def consultar_resolucion(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    _exigir_solicitud(
        db,
        id_solicitud,
    )

    return intervencion_service.consultar_resolucion(
        db,
        id_solicitud,
    )


@router.post(
    "/{id_solicitud}/resolucion/emitir",
    response_model=ResolucionEmitidaResponse,
)
def registrar_emision_resolucion(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    return (
        intervencion_service.registrar_resolucion_emitida(
            db,
            id_solicitud,
            usuario.id_usuario,
        )
    )


# ============================================================
# CONSULTAR INTERVENCIONES
# ============================================================

@router.get(
    "/{id_solicitud}/intervenciones",
    response_model=list[IntervencionResponse],
)
def listar_intervenciones(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    _exigir_solicitud(
        db,
        id_solicitud,
    )

    return intervenciones.listar(
        db,
        id_solicitud,
    )


# ============================================================
# CONVOCAR ESTUDIANTE
# ============================================================

@router.post(
    "/{id_solicitud}/intervenciones/convocar",
    response_model=ConvocatoriaResponse,
)
def convocar_estudiante(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    intervencion, notificacion = (
        intervencion_service.convocar(
            db,
            id_solicitud,
            usuario.id_usuario,
        )
    )

    # La convocatoria queda registrada antes
    # de contactar con Brevo.
    notificacion_solicitud_service.notificar_convocatoria(
        db,
        intervencion.id_intervencion,
    )

    db.refresh(intervencion)
    db.refresh(notificacion)

    return ConvocatoriaResponse(
        intervencion=(
            IntervencionResponse.model_validate(
                intervencion
            )
        ),
        notificacion=(
            NotificacionResponse.model_validate(
                notificacion
            )
        ),
    )


# ============================================================
# REGISTRAR FIRMA O REVISIÓN
# ============================================================

@router.post(
    "/{id_solicitud}/intervenciones/"
    "{id_intervencion}/revision",
    response_model=IntervencionResponse,
)
def registrar_revision(
    id_solicitud: int,
    id_intervencion: int,
    datos: RevisionPresencialRequest,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    return intervencion_service.registrar_revision(
        db,
        id_solicitud,
        usuario.id_usuario,
        datos,
        id_intervencion=id_intervencion,
    )


# ============================================================
# CONSULTAR NOTIFICACIONES
# ============================================================

@router.get(
    "/{id_solicitud}/notificaciones",
    response_model=list[NotificacionResponse],
)
def listar_notificaciones(
    id_solicitud: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    _exigir_solicitud(
        db,
        id_solicitud,
    )

    return notificaciones.listar(
        db,
        id_solicitud,
    )


# ============================================================
# REINTENTAR NOTIFICACIÓN
# ============================================================

@router.post(
    "/{id_solicitud}/notificaciones/"
    "{id_notificacion}/reenviar",
    response_model=NotificacionResponse,
)
def reintentar_envio(
    id_solicitud: int,
    id_notificacion: int,
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
):
    return (
        notificacion_solicitud_service
        .reintentar_notificacion(
            db,
            id_solicitud=id_solicitud,
            id_notificacion=id_notificacion,
        )
    )
