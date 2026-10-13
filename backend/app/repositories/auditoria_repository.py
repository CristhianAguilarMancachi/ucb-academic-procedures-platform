from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria


def crear_registro_auditoria(
    db: Session,
    *,
    accion: str,
    modulo: str,
    id_usuario_actor: int | None = None,
    entidad: str | None = None,
    id_entidad: str | None = None,
    exitoso: bool = True,
    detalle: dict[str, Any] | None = None,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> Auditoria:
    """
    Registra una acción relevante realizada en el sistema.

    Ejemplos:
    - modificación del estado de un usuario;
    - asignación o revocación de un rol;
    - cambio de correo principal;
    - bloqueo o desbloqueo de una cuenta.
    """
    auditoria = Auditoria(
        id_usuario_actor=id_usuario_actor,
        accion=accion.strip(),
        modulo=modulo.strip(),
        entidad=(
            entidad.strip()
            if entidad
            else None
        ),
        id_entidad=(
            id_entidad.strip()
            if id_entidad
            else None
        ),
        exitoso=exitoso,
        detalle=detalle,
        direccion_ip=direccion_ip,
        user_agent=user_agent,
    )

    db.add(auditoria)
    db.flush()
    db.refresh(auditoria)

    return auditoria


def obtener_auditoria_por_id(
    db: Session,
    id_auditoria: int,
) -> Auditoria | None:
    """
    Obtiene un registro de auditoría mediante su ID.
    """
    return db.get(
        Auditoria,
        id_auditoria,
    )


def listar_auditoria(
    db: Session,
    *,
    pagina: int = 1,
    por_pagina: int = 20,
    id_usuario_actor: int | None = None,
    modulo: str | None = None,
    accion: str | None = None,
    entidad: str | None = None,
    id_entidad: str | None = None,
    exitoso: bool | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
) -> tuple[Sequence[Auditoria], int]:
    """
    Lista registros de auditoría con filtros y paginación.
    """
    pagina = max(pagina, 1)
    por_pagina = min(
        max(por_pagina, 1),
        100,
    )

    filtros = []

    if id_usuario_actor is not None:
        filtros.append(
            Auditoria.id_usuario_actor
            == id_usuario_actor
        )

    if modulo:
        filtros.append(
            Auditoria.modulo == modulo.strip()
        )

    if accion:
        filtros.append(
            Auditoria.accion == accion.strip()
        )

    if entidad:
        filtros.append(
            Auditoria.entidad == entidad.strip()
        )

    if id_entidad:
        filtros.append(
            Auditoria.id_entidad
            == id_entidad.strip()
        )

    if exitoso is not None:
        filtros.append(
            Auditoria.exitoso.is_(exitoso)
        )

    if fecha_desde is not None:
        filtros.append(
            Auditoria.fecha_evento >= fecha_desde
        )

    if fecha_hasta is not None:
        filtros.append(
            Auditoria.fecha_evento <= fecha_hasta
        )

    consulta_total = select(
        func.count(
            Auditoria.id_auditoria
        )
    )

    if filtros:
        consulta_total = consulta_total.where(
            *filtros
        )

    total = int(
        db.scalar(consulta_total) or 0
    )

    consulta = select(
        Auditoria
    )

    if filtros:
        consulta = consulta.where(
            *filtros
        )

    consulta = (
        consulta
        .order_by(
            Auditoria.fecha_evento.desc()
        )
        .offset(
            (pagina - 1) * por_pagina
        )
        .limit(
            por_pagina
        )
    )

    registros = db.scalars(
        consulta
    ).all()

    return registros, total


def listar_auditoria_entidad(
    db: Session,
    *,
    entidad: str,
    id_entidad: str,
    limite: int = 50,
) -> Sequence[Auditoria]:
    """
    Obtiene el historial de cambios realizados sobre una
    entidad concreta.

    Ejemplo:
        entidad = "usuario"
        id_entidad = "25"
    """
    limite = min(
        max(limite, 1),
        100,
    )

    consulta = (
        select(Auditoria)
        .where(
            Auditoria.entidad
            == entidad.strip(),
            Auditoria.id_entidad
            == id_entidad.strip(),
        )
        .order_by(
            Auditoria.fecha_evento.desc()
        )
        .limit(limite)
    )

    return db.scalars(
        consulta
    ).all()


def listar_acciones_usuario_actor(
    db: Session,
    id_usuario_actor: int,
    *,
    limite: int = 50,
) -> Sequence[Auditoria]:
    """
    Devuelve las acciones recientes realizadas por un usuario.
    """
    limite = min(
        max(limite, 1),
        100,
    )

    consulta = (
        select(Auditoria)
        .where(
            Auditoria.id_usuario_actor
            == id_usuario_actor
        )
        .order_by(
            Auditoria.fecha_evento.desc()
        )
        .limit(limite)
    )

    return db.scalars(
        consulta
    ).all()


def contar_acciones(
    db: Session,
    *,
    modulo: str | None = None,
    accion: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
) -> int:
    """
    Cuenta acciones de auditoría según los filtros recibidos.
    """
    filtros = []

    if modulo:
        filtros.append(
            Auditoria.modulo == modulo.strip()
        )

    if accion:
        filtros.append(
            Auditoria.accion == accion.strip()
        )

    if fecha_desde is not None:
        filtros.append(
            Auditoria.fecha_evento >= fecha_desde
        )

    if fecha_hasta is not None:
        filtros.append(
            Auditoria.fecha_evento <= fecha_hasta
        )

    consulta = select(
        func.count(
            Auditoria.id_auditoria
        )
    )

    if filtros:
        consulta = consulta.where(
            *filtros
        )

    return int(
        db.scalar(consulta) or 0
    )

def actividad_reciente_usuario(db: Session, id_usuario: int, limite: int = 30) -> list[dict]:
    """Actividad propia y cambios administrativos sobre la cuenta, sin datos sensibles."""
    from sqlalchemy import literal, union_all, or_
    from app.models.evento_autenticacion import EventoAutenticacion
    auditoria = select(
        Auditoria.fecha_evento.label("fecha"), literal("auditoria").label("origen"),
        Auditoria.accion.label("accion"), Auditoria.exitoso.label("exitoso"),
    ).where(or_(
        Auditoria.id_usuario_actor == id_usuario,
        (Auditoria.entidad == "usuario") & (Auditoria.id_entidad == str(id_usuario)),
        (Auditoria.entidad == "usuario_rol")
        & (Auditoria.detalle["id_usuario"].as_string() == str(id_usuario)),
    ))
    autenticacion = select(
        EventoAutenticacion.fecha_evento.label("fecha"), literal("autenticacion").label("origen"),
        EventoAutenticacion.tipo_evento.label("accion"), EventoAutenticacion.exitoso.label("exitoso"),
    ).where(EventoAutenticacion.id_usuario == id_usuario)
    eventos = union_all(auditoria, autenticacion).subquery()
    return [dict(row) for row in db.execute(
        select(eventos).order_by(eventos.c.fecha.desc(), eventos.c.origen, eventos.c.accion).limit(limite)
    ).mappings()]
