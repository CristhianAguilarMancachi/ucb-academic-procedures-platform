from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento import (
    solicitud_administrativa_repository,
)
from app.schemas.gestion_seguimiento.solicitud_administrativa import (
    ListaSolicitudesAdministrativasResponse,
    RequisitoVerificacionResponse,
    RequisitoVerificarRequest,
    SolicitudAdministrativaDetalleResponse,
    SolicitudAdministrativaResumenResponse,
    SolicitudDatoAdministrativoResponse,
    SolicitudRecepcionResponse,
    SolicitudRequisitoAdministrativoResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)


class SolicitudAdministrativaServiceError(
    Exception
):
    """Error base de gestión administrativa."""


class SolicitudAdministrativaNoEncontradaError(
    SolicitudAdministrativaServiceError
):
    """La solicitud no existe o no está disponible para gestión."""


class SolicitudYaRecibidaError(
    SolicitudAdministrativaServiceError
):
    """La solicitud ya tiene una recepción registrada."""


class SolicitudNoPendienteRecepcionError(
    SolicitudAdministrativaServiceError
):
    """La solicitud no puede volver a recibirse."""


class SolicitudNoEstaEnRevisionError(
    SolicitudAdministrativaServiceError
):
    """La solicitud todavía no se encuentra en revisión."""


class RequisitoSolicitudNoEncontradoError(
    SolicitudAdministrativaServiceError
):
    """El requisito solicitado no existe."""


class RequisitoNoPerteneceSolicitudError(
    SolicitudAdministrativaServiceError
):
    """El requisito no pertenece a la solicitud indicada."""


class RequisitoEconomicoRequiereApiError(
    SolicitudAdministrativaServiceError
):
    """
    Los requisitos económicos no pueden aprobarse
    manualmente.
    """


# ============================================================
# HELPERS
# ============================================================


def _obtener_solicitud(
    db: Session,
    id_solicitud: int,
):
    solicitud = (
        solicitud_administrativa_repository
        .obtener_solicitud_administrativa_por_id(
            db,
            id_solicitud,
        )
    )

    if solicitud is None:
        raise (
            SolicitudAdministrativaNoEncontradaError(
                "La solicitud no existe o no está "
                "disponible para gestión administrativa."
            )
        )

    return solicitud


def _construir_detalle(
    db: Session,
    id_solicitud: int,
) -> SolicitudAdministrativaDetalleResponse:
    solicitud = _obtener_solicitud(
        db,
        id_solicitud,
    )

    recepcion = (
        solicitud_administrativa_repository
        .obtener_recepcion_por_solicitud(
            db,
            id_solicitud,
        )
    )

    return SolicitudAdministrativaDetalleResponse(
        id_solicitud=solicitud.id_solicitud,
        id_solicitante=solicitud.id_solicitante,
        id_tramite=solicitud.id_tramite,
        nombre_tramite=solicitud.tramite.nombre,
        estado=solicitud.estado,
        fecha_creacion=solicitud.fecha_creacion,
        fecha_envio=solicitud.fecha_envio,
        datos=[
            SolicitudDatoAdministrativoResponse.model_validate(
                dato
            )
            for dato in solicitud.datos
        ],
        requisitos=[
            SolicitudRequisitoAdministrativoResponse.model_validate(
                requisito
            )
            for requisito in sorted(
                solicitud.requisitos,
                key=lambda item: (
                    item.orden,
                    item.id_solicitud_requisito,
                ),
            )
        ],
        recepcion=(
            SolicitudRecepcionResponse.model_validate(
                recepcion
            )
            if recepcion is not None
            else None
        ),
    )


# ============================================================
# BANDEJA
# ============================================================


def listar_bandeja_administrativa(
    db: Session,
    *,
    estado: str | None = None,
    id_tramite: int | None = None,
    id_solicitud: int | None = None,
    pagina: int = 1,
    limite: int = 20,
) -> ListaSolicitudesAdministrativasResponse:
    solicitudes, total = (
        solicitud_administrativa_repository
        .listar_solicitudes_administrativas(
            db,
            estado=estado,
            id_tramite=id_tramite,
            id_solicitud=id_solicitud,
            pagina=pagina,
            limite=limite,
        )
    )

    return ListaSolicitudesAdministrativasResponse(
        items=[
            SolicitudAdministrativaResumenResponse(
                id_solicitud=solicitud.id_solicitud,
                id_solicitante=solicitud.id_solicitante,
                id_tramite=solicitud.id_tramite,
                nombre_tramite=solicitud.tramite.nombre,
                estado=solicitud.estado,
                fecha_creacion=solicitud.fecha_creacion,
                fecha_envio=solicitud.fecha_envio,
            )
            for solicitud in solicitudes
        ],
        total=total,
        pagina=max(
            pagina,
            1,
        ),
        limite=min(
            max(
                limite,
                1,
            ),
            100,
        ),
    )


def obtener_detalle_administrativo(
    db: Session,
    *,
    id_solicitud: int,
) -> SolicitudAdministrativaDetalleResponse:
    return _construir_detalle(
        db,
        id_solicitud,
    )


# ============================================================
# RECEPCIÓN
# ============================================================


def recibir_solicitud(
    db: Session,
    *,
    id_solicitud: int,
    id_usuario_receptor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SolicitudAdministrativaDetalleResponse:
    """
    Registra la recepción administrativa inicial.

    Única transición realizada en esta fase:

        pendiente_recepcion
                ↓
            en_revision

    No se asigna unidad.
    No se asigna etapa.
    No se deriva la solicitud.
    """
    solicitud = _obtener_solicitud(
        db,
        id_solicitud,
    )

    if solicitud.estado != "pendiente_recepcion":
        raise SolicitudNoPendienteRecepcionError(
            "La solicitud ya no se encuentra "
            "pendiente de recepción."
        )

    recepcion_existente = (
        solicitud_administrativa_repository
        .obtener_recepcion_por_solicitud(
            db,
            id_solicitud,
        )
    )

    if recepcion_existente is not None:
        raise SolicitudYaRecibidaError(
            "La solicitud ya fue recibida."
        )

    fecha_recepcion = datetime.now(
        timezone.utc
    )

    try:
        solicitud_administrativa_repository.crear_recepcion(
            db,
            id_solicitud=id_solicitud,
            id_usuario_receptor=(
                id_usuario_receptor
            ),
            fecha_recepcion=fecha_recepcion,
        )

        solicitud_administrativa_repository.marcar_solicitud_en_revision(
            db,
            solicitud,
        )

        registrar_accion_simple(
            db,
            accion="recibir_solicitud",
            modulo="gestion_seguimiento",
            id_usuario_actor=id_usuario_receptor,
            entidad="solicitud",
            id_entidad=str(
                id_solicitud
            ),
            exitoso=True,
            detalle={
                "estado_anterior": (
                    "pendiente_recepcion"
                ),
                "estado_nuevo": "en_revision",
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        return _construir_detalle(
            db,
            id_solicitud,
        )

    except IntegrityError as exc:
        db.rollback()

        raise SolicitudYaRecibidaError(
            "La solicitud ya fue recibida."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ============================================================
# VERIFICACIÓN MANUAL DE REQUISITOS NO ECONÓMICOS
# ============================================================


def verificar_requisito_manual(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitud_requisito: int,
    id_usuario_verificador: int,
    datos: RequisitoVerificarRequest,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> RequisitoVerificacionResponse:
    """
    Verifica manualmente un requisito NO económico.

    Los requisitos económicos deben utilizar exclusivamente
    la integración con la API de facturación/pagos.
    """
    solicitud = _obtener_solicitud(
        db,
        id_solicitud,
    )

    if solicitud.estado != "en_revision":
        raise SolicitudNoEstaEnRevisionError(
            "La solicitud debe estar en revisión "
            "antes de verificar sus requisitos."
        )

    requisito = (
        solicitud_administrativa_repository
        .obtener_requisito_solicitud_por_id(
            db,
            id_solicitud_requisito,
        )
    )

    if requisito is None:
        raise RequisitoSolicitudNoEncontradoError(
            "El requisito indicado no existe."
        )

    if requisito.id_solicitud != id_solicitud:
        raise RequisitoNoPerteneceSolicitudError(
            "El requisito no pertenece a la solicitud."
        )

    if requisito.es_economico:
        raise RequisitoEconomicoRequiereApiError(
            "Los requisitos económicos deben verificarse "
            "mediante la API de pagos."
        )

    estado_anterior = (
        requisito.estado_verificacion
    )

    fecha_verificacion = datetime.now(
        timezone.utc
    )

    try:
        requisito = (
            solicitud_administrativa_repository
            .actualizar_verificacion_requisito(
                db,
                requisito,
                estado_verificacion=datos.estado,
                id_usuario_verificador=(
                    id_usuario_verificador
                ),
                fecha_verificacion=(
                    fecha_verificacion
                ),
                detalle_verificacion=(
                    datos.detalle
                ),
            )
        )

        registrar_accion_simple(
            db,
            accion="verificar_requisito_solicitud",
            modulo="gestion_seguimiento",
            id_usuario_actor=id_usuario_verificador,
            entidad="solicitud_requisito",
            id_entidad=str(
                requisito.id_solicitud_requisito
            ),
            exitoso=True,
            detalle={
                "id_solicitud": id_solicitud,
                "estado_anterior": estado_anterior,
                "estado_nuevo": (
                    requisito.estado_verificacion
                ),
                "es_economico": False,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        return (
            RequisitoVerificacionResponse
            .model_validate(
                requisito
            )
        )

    except Exception:
        db.rollback()
        raise