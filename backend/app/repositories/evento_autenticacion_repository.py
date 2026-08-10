from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.evento_autenticacion import EventoAutenticacion


def crear_evento_autenticacion(
    db: Session,
    *,
    tipo_evento: str,
    exitoso: bool,
    id_usuario: int | None = None,
    correo_intentado: str | None = None,
    motivo_fallo: str | None = None,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> EventoAutenticacion:
    """
    Registra un evento relacionado con autenticación.

    Ejemplos:
    - registro de una cuenta;
    - inicio de sesión exitoso;
    - inicio de sesión fallido;
    - renovación de sesión;
    - cierre de sesión;
    - recuperación de contraseña.
    """
    evento = EventoAutenticacion(
        id_usuario=id_usuario,
        correo_intentado=(
            correo_intentado.strip()
            if correo_intentado
            else None
        ),
        tipo_evento=tipo_evento,
        exitoso=exitoso,
        motivo_fallo=motivo_fallo,
        direccion_ip=direccion_ip,
        user_agent=user_agent,
    )

    db.add(evento)
    db.flush()
    db.refresh(evento)

    return evento


def obtener_evento_autenticacion_por_id(
    db: Session,
    id_evento_autenticacion: int,
) -> EventoAutenticacion | None:
    """
    Obtiene un evento de autenticación mediante su ID.
    """
    return db.get(
        EventoAutenticacion,
        id_evento_autenticacion,
    )


def listar_eventos_autenticacion(
    db: Session,
    *,
    pagina: int = 1,
    por_pagina: int = 20,
    id_usuario: int | None = None,
    correo: str | None = None,
    tipo_evento: str | None = None,
    exitoso: bool | None = None,
    direccion_ip: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
) -> tuple[Sequence[EventoAutenticacion], int]:
    """
    Lista eventos de autenticación con filtros y paginación.
    """
    pagina = max(pagina, 1)
    por_pagina = min(
        max(por_pagina, 1),
        100,
    )

    filtros = []

    if id_usuario is not None:
        filtros.append(
            EventoAutenticacion.id_usuario == id_usuario
        )

    if correo:
        filtros.append(
            EventoAutenticacion.correo_intentado
            == correo.strip()
        )

    if tipo_evento:
        filtros.append(
            EventoAutenticacion.tipo_evento
            == tipo_evento
        )

    if exitoso is not None:
        filtros.append(
            EventoAutenticacion.exitoso.is_(exitoso)
        )

    if direccion_ip:
        filtros.append(
            EventoAutenticacion.direccion_ip
            == direccion_ip
        )

    if fecha_desde is not None:
        filtros.append(
            EventoAutenticacion.fecha_evento
            >= fecha_desde
        )

    if fecha_hasta is not None:
        filtros.append(
            EventoAutenticacion.fecha_evento
            <= fecha_hasta
        )

    consulta_total = select(
        func.count(
            EventoAutenticacion.id_evento_autenticacion
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
        EventoAutenticacion
    )

    if filtros:
        consulta = consulta.where(
            *filtros
        )

    consulta = (
        consulta
        .order_by(
            EventoAutenticacion.fecha_evento.desc()
        )
        .offset(
            (pagina - 1) * por_pagina
        )
        .limit(
            por_pagina
        )
    )

    eventos = db.scalars(
        consulta
    ).all()

    return eventos, total


def contar_intentos_fallidos(
    db: Session,
    *,
    correo: str,
    fecha_desde: datetime,
) -> int:
    """
    Cuenta intentos fallidos realizados con un correo desde
    una fecha determinada.

    Se utilizará para aplicar límites de intentos de acceso.
    """
    consulta = select(
        func.count(
            EventoAutenticacion.id_evento_autenticacion
        )
    ).where(
        EventoAutenticacion.correo_intentado
        == correo.strip(),
        EventoAutenticacion.tipo_evento
        == "inicio_sesion",
        EventoAutenticacion.exitoso.is_(False),
        EventoAutenticacion.fecha_evento
        >= fecha_desde,
    )

    return int(
        db.scalar(consulta) or 0
    )


def obtener_ultimo_inicio_sesion_exitoso(
    db: Session,
    id_usuario: int,
) -> EventoAutenticacion | None:
    """
    Obtiene el inicio de sesión exitoso más reciente de una
    cuenta.
    """
    consulta = (
        select(EventoAutenticacion)
        .where(
            EventoAutenticacion.id_usuario
            == id_usuario,
            EventoAutenticacion.tipo_evento
            == "inicio_sesion",
            EventoAutenticacion.exitoso.is_(True),
        )
        .order_by(
            EventoAutenticacion.fecha_evento.desc()
        )
        .limit(1)
    )

    return db.scalars(
        consulta
    ).first()


def listar_eventos_usuario(
    db: Session,
    id_usuario: int,
    *,
    limite: int = 20,
) -> Sequence[EventoAutenticacion]:
    """
    Devuelve los eventos recientes de un usuario.
    """
    limite = min(
        max(limite, 1),
        100,
    )

    consulta = (
        select(EventoAutenticacion)
        .where(
            EventoAutenticacion.id_usuario
            == id_usuario
        )
        .order_by(
            EventoAutenticacion.fecha_evento.desc()
        )
        .limit(limite)
    )

    return db.scalars(
        consulta
    ).all()