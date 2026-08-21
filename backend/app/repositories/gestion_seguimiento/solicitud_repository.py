from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.gestion_seguimiento.solicitud import Solicitud
from app.models.gestion_seguimiento.solicitud_dato import (
    SolicitudDato,
)
from app.models.gestion_seguimiento.solicitud_requisito import (
    SolicitudRequisito,
)


# ============================================================
# SOLICITUD
# ============================================================


def crear_solicitud(
    db: Session,
    *,
    id_solicitante: int,
    id_tramite: int,
) -> Solicitud:
    """
    Crea una solicitud en estado borrador.

    La transacción queda pendiente de confirmación
    por parte del service.
    """
    solicitud = Solicitud(
        id_solicitante=id_solicitante,
        id_tramite=id_tramite,
        estado="borrador",
    )

    db.add(solicitud)
    db.flush()
    db.refresh(solicitud)

    return solicitud


def obtener_solicitud_por_id(
    db: Session,
    id_solicitud: int,
) -> Solicitud | None:
    """
    Obtiene una solicitud sin cargar relaciones adicionales.
    """
    return db.get(
        Solicitud,
        id_solicitud,
    )


def obtener_solicitud_por_id_completa(
    db: Session,
    id_solicitud: int,
) -> Solicitud | None:
    """
    Obtiene una solicitud con trámite, datos y requisitos.
    """
    consulta = (
        select(Solicitud)
        .where(
            Solicitud.id_solicitud == id_solicitud,
        )
        .options(
            selectinload(
                Solicitud.tramite,
            ),
            selectinload(
                Solicitud.datos,
            ),
            selectinload(
                Solicitud.requisitos,
            ),
        )
    )

    return db.scalars(
        consulta
    ).unique().one_or_none()


def obtener_solicitud_usuario_por_id(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitante: int,
    completa: bool = False,
) -> Solicitud | None:
    """
    Obtiene una solicitud únicamente si pertenece
    al solicitante indicado.
    """
    consulta = select(
        Solicitud
    ).where(
        Solicitud.id_solicitud == id_solicitud,
        Solicitud.id_solicitante == id_solicitante,
    )

    if completa:
        consulta = consulta.options(
            selectinload(
                Solicitud.tramite,
            ),
            selectinload(
                Solicitud.datos,
            ),
            selectinload(
                Solicitud.requisitos,
            ),
        )

    return db.scalars(
        consulta
    ).unique().one_or_none()


def listar_solicitudes_usuario(
    db: Session,
    *,
    id_solicitante: int,
    estado: str | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> tuple[Sequence[Solicitud], int]:
    """
    Lista las solicitudes de un usuario.

    Permite filtrar por estado y aplica paginación.
    """
    pagina = max(
        pagina,
        1,
    )

    por_pagina = min(
        max(
            por_pagina,
            1,
        ),
        100,
    )

    filtros = [
        Solicitud.id_solicitante == id_solicitante,
    ]

    if estado is not None:
        filtros.append(
            Solicitud.estado == estado,
        )

    total = db.scalar(
        select(func.count())
        .select_from(Solicitud)
        .where(*filtros)
    ) or 0

    consulta = (
        select(Solicitud)
        .where(*filtros)
        .options(
            selectinload(
                Solicitud.tramite,
            ),
        )
        .order_by(
            Solicitud.fecha_actualizacion.desc(),
            Solicitud.id_solicitud.desc(),
        )
        .offset(
            (pagina - 1) * por_pagina,
        )
        .limit(
            por_pagina,
        )
    )

    solicitudes = db.scalars(
        consulta
    ).all()

    return solicitudes, int(total)


def marcar_solicitud_enviada(
    db: Session,
    solicitud: Solicitud,
    *,
    fecha_envio: datetime,
) -> Solicitud:
    """
    Cambia formalmente un borrador a pendiente de recepción.
    """
    solicitud.estado = "pendiente_recepcion"
    solicitud.fecha_envio = fecha_envio

    db.flush()
    db.refresh(solicitud)

    return solicitud


def eliminar_solicitud(
    db: Session,
    solicitud: Solicitud,
) -> None:
    """
    Elimina físicamente una solicitud.

    El service debe garantizar que solamente se eliminen
    solicitudes en estado borrador.
    """
    db.delete(solicitud)
    db.flush()


# ============================================================
# DATOS DINÁMICOS DE SOLICITUD
# ============================================================


def obtener_dato_solicitud(
    db: Session,
    *,
    id_solicitud: int,
    id_campo: int,
) -> SolicitudDato | None:
    """
    Obtiene el valor guardado para un campo de una solicitud.
    """
    consulta = select(
        SolicitudDato
    ).where(
        SolicitudDato.id_solicitud == id_solicitud,
        SolicitudDato.id_campo == id_campo,
    )

    return db.scalars(
        consulta
    ).one_or_none()


def listar_datos_solicitud(
    db: Session,
    id_solicitud: int,
) -> Sequence[SolicitudDato]:
    """
    Lista los datos guardados en una solicitud.
    """
    consulta = (
        select(SolicitudDato)
        .where(
            SolicitudDato.id_solicitud == id_solicitud,
        )
        .order_by(
            SolicitudDato.id_solicitud_dato.asc(),
        )
    )

    return db.scalars(
        consulta
    ).all()


def guardar_dato_solicitud(
    db: Session,
    *,
    id_solicitud: int,
    id_campo: int,
    valor: Any,
) -> SolicitudDato:
    """
    Crea o actualiza el valor de un campo de la solicitud.
    """
    dato = obtener_dato_solicitud(
        db,
        id_solicitud=id_solicitud,
        id_campo=id_campo,
    )

    if dato is None:
        dato = SolicitudDato(
            id_solicitud=id_solicitud,
            id_campo=id_campo,
            valor=valor,
        )

        db.add(dato)

    else:
        dato.valor = valor

    db.flush()
    db.refresh(dato)

    return dato


def eliminar_dato_solicitud(
    db: Session,
    dato: SolicitudDato,
) -> None:
    """
    Elimina un dato guardado del borrador.
    """
    db.delete(dato)
    db.flush()


# ============================================================
# SNAPSHOT DE REQUISITOS
# ============================================================


def crear_requisito_solicitud(
    db: Session,
    *,
    id_solicitud: int,
    id_requisito_origen: int | None,
    nombre: str,
    descripcion: str | None,
    obligatorio: bool,
    orden: int,
    id_requisito_economico_origen: int | None = None,
    concepto_economico: str | None = None,
    monto_economico: Decimal | None = None,
    moneda: str | None = None,
    gestion: int | None = None,
    codigo_concepto_externo: str | None = None,
    numero_factura: str | None = None,
) -> SolicitudRequisito:
    """
    Crea la fotografía histórica de un requisito
    cuando se envía formalmente una solicitud.

    Para un requisito económico puede conservar también
    el número de factura proporcionado por el solicitante.
    """
    requisito = SolicitudRequisito(
        id_solicitud=id_solicitud,
        id_requisito_origen=id_requisito_origen,
        nombre=nombre,
        descripcion=descripcion,
        obligatorio=obligatorio,
        orden=orden,
        id_requisito_economico_origen=(
            id_requisito_economico_origen
        ),
        concepto_economico=concepto_economico,
        monto_economico=monto_economico,
        moneda=moneda,
        gestion=gestion,
        codigo_concepto_externo=(
            codigo_concepto_externo
        ),
        numero_factura=numero_factura,
    )

    db.add(requisito)
    db.flush()
    db.refresh(requisito)

    return requisito


def listar_requisitos_solicitud(
    db: Session,
    id_solicitud: int,
) -> Sequence[SolicitudRequisito]:
    """
    Lista la fotografía de requisitos de una solicitud.
    """
    consulta = (
        select(SolicitudRequisito)
        .where(
            SolicitudRequisito.id_solicitud
            == id_solicitud,
        )
        .order_by(
            SolicitudRequisito.orden.asc(),
            SolicitudRequisito.id_solicitud_requisito.asc(),
        )
    )

    return db.scalars(
        consulta
    ).all()


def contar_requisitos_solicitud(
    db: Session,
    id_solicitud: int,
) -> int:
    """
    Cuenta los requisitos históricos generados
    para una solicitud.
    """
    total = db.scalar(
        select(func.count())
        .select_from(SolicitudRequisito)
        .where(
            SolicitudRequisito.id_solicitud
            == id_solicitud,
        )
    )

    return int(total or 0)