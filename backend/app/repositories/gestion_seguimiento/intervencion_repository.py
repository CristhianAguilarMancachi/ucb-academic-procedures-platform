
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gestion_seguimiento import SolicitudIntervencion


def listar(
    db: Session,
    id_solicitud: int,
) -> list[SolicitudIntervencion]:
    return list(
        db.scalars(
            select(SolicitudIntervencion)
            .where(
                SolicitudIntervencion.id_solicitud
                == id_solicitud
            )
            .order_by(
                SolicitudIntervencion.id_intervencion
            )
        )
    )


def obtener_ultima(
    db: Session,
    id_solicitud: int,
) -> SolicitudIntervencion | None:
    return db.scalar(
        select(SolicitudIntervencion)
        .where(
            SolicitudIntervencion.id_solicitud
            == id_solicitud
        )
        .order_by(
            SolicitudIntervencion.id_intervencion.desc()
        )
        .limit(1)
    )


def crear_convocatoria(
    db: Session,
    *,
    id_solicitud: int,
    tipo: str,
    actor: int,
) -> SolicitudIntervencion:
    item = SolicitudIntervencion(
        id_solicitud=id_solicitud,
        tipo=tipo,
        estado="convocada",
        id_usuario_convocatoria=actor,
    )

    db.add(item)
    db.flush()

    return item


def registrar_revision(
    db: Session,
    intervencion: SolicitudIntervencion,
    *,
    resultado: str,
    fecha_revision: date,
    motivo_desacuerdo: str | None,
    actor: int,
) -> SolicitudIntervencion:
    from app.core.security import utc_now

    intervencion.estado = resultado
    intervencion.fecha_revision = fecha_revision
    intervencion.motivo_desacuerdo = motivo_desacuerdo
    intervencion.id_usuario_registro = actor
    intervencion.fecha_registro = utc_now()

    db.flush()

    return intervencion
