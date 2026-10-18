
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models.gestion_seguimiento import (
    SolicitudRecepcion,
    SolicitudResultado,
)
from app.repositories.gestion_seguimiento import (
    seguimiento_repository as repo,
)
from app.schemas.gestion_seguimiento.seguimiento import (
    ResultadoRegistrarRequest,
)
from app.services.gestion_seguimiento.intervencion_service import (
    exigir_intervencion_completada,
)
from app.services.gestion_seguimiento.seguimiento_service import (
    SeguimientoError,
    evento,
    exigir_estado,
    exigir_requisitos,
    exigir_sin_observaciones,
    obtener_para_accion,
    transaccion,
)


@transaccion
def iniciar_atencion(
    db: Session,
    id_solicitud: int,
    actor: int,
) -> None:
    """
    Registra la recepción y el inicio de atención
    mediante una única operación administrativa.
    """

    solicitud = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        solicitud,
        "pendiente_recepcion",
        "en_revision",
    )

    recepcion = db.scalar(
        select(SolicitudRecepcion).where(
            SolicitudRecepcion.id_solicitud
            == id_solicitud
        )
    )

    if recepcion is None:
        db.add(
            SolicitudRecepcion(
                id_solicitud=id_solicitud,
                id_usuario_receptor=actor,
                fecha_recepcion=utc_now(),
            )
        )

    # Compatibilidad durante la transición:
    # la captura definitiva de esta configuración
    # se integrará al envío de solicitudes.
    if (
        solicitud.tipo_intervencion == "ninguna"
        and solicitud.tramite.tipo_intervencion
        != "ninguna"
    ):
        solicitud.tipo_intervencion = (
            solicitud.tramite.tipo_intervencion
        )

    solicitud.estado = "en_proceso"
    solicitud.fecha_actualizacion = utc_now()

    evento(
        db,
        solicitud,
        actor,
        "atencion_iniciada",
        "La solicitud fue recibida y "
        "su atención fue iniciada.",
    )


@transaccion
def registrar_resultado(
    db: Session,
    id_solicitud: int,
    actor: int,
    datos: ResultadoRegistrarRequest,
) -> None:
    """
    Registra el resultado sin exigir avances
    por etapas administrativas internas.
    """

    solicitud = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        solicitud,
        "en_proceso",
    )

    exigir_sin_observaciones(
        db,
        id_solicitud,
    )

    exigir_requisitos(
        solicitud.requisitos,
    )

    exigir_intervencion_completada(
        db,
        solicitud,
    )

    if repo.obtener_resultado(
        db,
        id_solicitud,
    ) is not None:
        raise SeguimientoError(
            "La solicitud ya tiene un "
            "resultado registrado."
        )

    tipo = (
        solicitud.tipo_finalizacion
        or datos.tipo_finalizacion
    )

    if tipo not in (
        "entrega",
        "resultado_registrado",
        "externo",
    ):
        raise SeguimientoError(
            "El trámite no tiene una modalidad "
            "de finalización válida."
        )

    if (
        solicitud.tipo_finalizacion is not None
        and datos.tipo_finalizacion is not None
        and solicitud.tipo_finalizacion
        != datos.tipo_finalizacion
    ):
        raise SeguimientoError(
            "No se puede modificar la modalidad "
            "de finalización de la solicitud."
        )

    solicitud.tipo_finalizacion = tipo

    db.add(
        SolicitudResultado(
            id_solicitud=id_solicitud,
            tipo_finalizacion=tipo,
            detalle=datos.detalle,
            id_usuario_registro=actor,
        )
    )

    evento(
        db,
        solicitud,
        actor,
        "resultado_registrado",
        datos.detalle
        or "Resultado administrativo registrado.",
    )

    solicitud.estado = (
        "lista_para_entrega"
        if tipo == "entrega"
        else "finalizada"
    )

    solicitud.fecha_actualizacion = utc_now()

    evento(
        db,
        solicitud,
        actor,
        (
            "lista_para_entrega"
            if tipo == "entrega"
            else "solicitud_finalizada"
        ),
        (
            "Disponible para recojo."
            if tipo == "entrega"
            else "Solicitud finalizada."
        ),
    )
