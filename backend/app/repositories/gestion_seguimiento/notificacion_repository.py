
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models.gestion_seguimiento import SolicitudNotificacion


def listar(
    db: Session,
    id_solicitud: int,
) -> list[SolicitudNotificacion]:
    return list(
        db.scalars(
            select(SolicitudNotificacion)
            .where(
                SolicitudNotificacion.id_solicitud
                == id_solicitud
            )
            .order_by(
                SolicitudNotificacion.id_notificacion
            )
        )
    )


def obtener_convocatoria(
    db: Session,
    id_intervencion: int,
) -> SolicitudNotificacion | None:
    return db.scalar(
        select(SolicitudNotificacion)
        .where(
            SolicitudNotificacion.id_intervencion
            == id_intervencion,
            SolicitudNotificacion.tipo == "convocatoria",
        )
    )


def obtener_resultado(
    db: Session,
    id_solicitud: int,
) -> SolicitudNotificacion | None:
    return db.scalar(
        select(SolicitudNotificacion)
        .where(
            SolicitudNotificacion.id_solicitud
            == id_solicitud,
            SolicitudNotificacion.tipo == "resultado",
        )
    )


def crear(
    db: Session,
    *,
    id_solicitud: int,
    tipo: str,
    destinatario: str,
    asunto: str,
    contenido_texto: str,
    id_intervencion: int | None = None,
) -> SolicitudNotificacion:
    item = SolicitudNotificacion(
        id_solicitud=id_solicitud,
        id_intervencion=id_intervencion,
        tipo=tipo,
        estado="pendiente",
        destinatario=destinatario,
        asunto=asunto,
        contenido_texto=contenido_texto,
    )

    db.add(item)
    db.flush()

    return item


def registrar_intento(
    db: Session,
    notificacion: SolicitudNotificacion,
    *,
    enviado: bool,
    error: str | None = None,
    referencia_externa: str | None = None,
) -> SolicitudNotificacion:
    if notificacion.estado == "enviado":
        return notificacion

    ahora = utc_now()

    notificacion.intentos += 1
    notificacion.fecha_ultimo_intento = ahora

    notificacion.estado = (
        "enviado" if enviado else "fallido"
    )

    notificacion.fecha_envio = (
        ahora if enviado else None
    )

    notificacion.ultimo_error = (
        None
        if enviado
        else (error or "No se pudo enviar el correo.")[:2000]
    )

    notificacion.referencia_externa = (
        referencia_externa if enviado else None
    )

    db.flush()

    return notificacion
