
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.gestion_seguimiento import (
    PerfilAcademico,
    Solicitud,
    SolicitudDato,
    SolicitudHistorial,
    SolicitudObservacion,
    SolicitudPagoVerificacion,
    SolicitudRequisito,
    SolicitudResultado,
)


def bloquear_solicitud(
    db: Session,
    id_solicitud: int,
) -> Solicitud | None:
    return db.scalar(
        select(Solicitud)
        .where(Solicitud.id_solicitud == id_solicitud)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def obtener_solicitud_completa(
    db: Session,
    id_solicitud: int,
) -> Solicitud | None:
    return db.scalar(
        select(Solicitud)
        .where(Solicitud.id_solicitud == id_solicitud)
        .options(
            selectinload(Solicitud.tramite),
            selectinload(Solicitud.solicitante),
            selectinload(Solicitud.datos).selectinload(
                SolicitudDato.campo
            ),
            selectinload(Solicitud.requisitos),
        )
        .execution_options(populate_existing=True)
    )


def listar_observaciones(
    db: Session,
    id_solicitud: int,
) -> list[SolicitudObservacion]:
    return list(
        db.scalars(
            select(SolicitudObservacion)
            .where(
                SolicitudObservacion.id_solicitud == id_solicitud
            )
            .order_by(
                SolicitudObservacion.fecha_observacion,
                SolicitudObservacion.id_observacion,
            )
        )
    )


def listar_historial(
    db: Session,
    id_solicitud: int,
    *,
    solo_visible: bool = False,
) -> list[SolicitudHistorial]:
    consulta = select(SolicitudHistorial).where(
        SolicitudHistorial.id_solicitud == id_solicitud
    )

    if solo_visible:
        consulta = consulta.where(
            SolicitudHistorial.visible_solicitante.is_(True)
        )

    consulta = consulta.order_by(
        SolicitudHistorial.fecha_evento,
        SolicitudHistorial.id_historial,
    )

    return list(db.scalars(consulta))


def registrar_historial(
    db: Session,
    id_solicitud: int,
    id_usuario_actor: int,
    evento: str,
    detalle: str,
    *,
    visible_solicitante: bool = True,
    id_solicitud_requisito: int | None = None,
) -> None:
    registro = SolicitudHistorial(
        id_solicitud=id_solicitud,
        id_usuario_actor=id_usuario_actor,
        evento=evento,
        detalle=detalle,
        visible_solicitante=visible_solicitante,
        id_solicitud_requisito=id_solicitud_requisito,
    )

    db.add(registro)
    db.flush()


def obtener_resultado(
    db: Session,
    id_solicitud: int,
) -> SolicitudResultado | None:
    return db.scalar(
        select(SolicitudResultado).where(
            SolicitudResultado.id_solicitud == id_solicitud
        )
    )




def obtener_perfil(
    db: Session,
    id_usuario: int,
) -> PerfilAcademico | None:
    return db.scalar(
        select(PerfilAcademico).where(
            PerfilAcademico.id_usuario == id_usuario
        )
    )


def listar_pagos(
    db: Session,
    id_solicitud: int,
) -> list[SolicitudPagoVerificacion]:
    return list(
        db.scalars(
            select(SolicitudPagoVerificacion)
            .join(SolicitudRequisito)
            .where(
                SolicitudRequisito.id_solicitud == id_solicitud
            )
            .order_by(
                SolicitudPagoVerificacion.fecha_verificacion,
                SolicitudPagoVerificacion.id_verificacion_pago,
            )
        )
    )
