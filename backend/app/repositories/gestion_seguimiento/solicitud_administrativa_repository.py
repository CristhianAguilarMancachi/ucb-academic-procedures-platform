from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.gestion_seguimiento.solicitud import Solicitud
from app.models.gestion_seguimiento.solicitud_recepcion import (
    SolicitudRecepcion,
)
from app.models.gestion_seguimiento.solicitud_requisito import (
    SolicitudRequisito,
)


# ============================================================
# BANDEJA ADMINISTRATIVA
# ============================================================


def listar_solicitudes_administrativas(
    db: Session,
    *,
    estado: str | None = None,
    id_tramite: int | None = None,
    id_solicitud: int | None = None,
    pagina: int = 1,
    limite: int = 20,
) -> tuple[Sequence[Solicitud], int]:
    """
    Lista solicitudes visibles para gestión administrativa.

    En Fase 3 solamente se consideran:
    - pendiente_recepcion
    - en_revision

    No se filtra por unidad porque todavía no conocemos
    institucionalmente qué unidad recibe cada trámite.
    """
    pagina = max(
        pagina,
        1,
    )

    limite = min(
        max(
            limite,
            1,
        ),
        100,
    )

    filtros = [
        Solicitud.estado.in_(
            (
                "pendiente_recepcion",
                "en_revision",
            )
        )
    ]

    if estado is not None:
        filtros.append(
            Solicitud.estado == estado
        )

    if id_tramite is not None:
        filtros.append(
            Solicitud.id_tramite == id_tramite
        )

    if id_solicitud is not None:
        filtros.append(
            Solicitud.id_solicitud == id_solicitud
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
                Solicitud.tramite
            ),
        )
        .order_by(
            Solicitud.fecha_envio.asc(),
            Solicitud.id_solicitud.asc(),
        )
        .offset(
            (pagina - 1) * limite
        )
        .limit(
            limite
        )
    )

    solicitudes = db.scalars(
        consulta
    ).all()

    return solicitudes, int(total)


def obtener_solicitud_administrativa_por_id(
    db: Session,
    id_solicitud: int,
) -> Solicitud | None:
    """
    Obtiene una solicitud con toda la información necesaria
    para la revisión administrativa.
    """
    consulta = (
        select(Solicitud)
        .where(
            Solicitud.id_solicitud == id_solicitud,
            Solicitud.estado.in_(
                (
                    "pendiente_recepcion",
                    "en_revision",
                )
            ),
        )
        .options(
            selectinload(
                Solicitud.tramite
            ),
            selectinload(
                Solicitud.datos
            ),
            selectinload(
                Solicitud.requisitos
            ),
        )
    )

    return db.scalars(
        consulta
    ).unique().one_or_none()


# ============================================================
# RECEPCIÓN
# ============================================================


def obtener_recepcion_por_solicitud(
    db: Session,
    id_solicitud: int,
) -> SolicitudRecepcion | None:
    consulta = select(
        SolicitudRecepcion
    ).where(
        SolicitudRecepcion.id_solicitud
        == id_solicitud
    )

    return db.scalars(
        consulta
    ).one_or_none()


def crear_recepcion(
    db: Session,
    *,
    id_solicitud: int,
    id_usuario_receptor: int,
    fecha_recepcion: datetime,
) -> SolicitudRecepcion:
    """
    Registra la recepción inicial de una solicitud.

    No se asigna unidad ni etapa.
    """
    recepcion = SolicitudRecepcion(
        id_solicitud=id_solicitud,
        id_usuario_receptor=id_usuario_receptor,
        fecha_recepcion=fecha_recepcion,
    )

    db.add(recepcion)
    db.flush()
    db.refresh(recepcion)

    return recepcion


def marcar_solicitud_en_revision(
    db: Session,
    solicitud: Solicitud,
) -> Solicitud:
    """
    Cambia pendiente_recepcion a en_revision.

    Esto NO representa el inicio de una etapa institucional.
    """
    solicitud.estado = "en_revision"

    db.flush()
    db.refresh(solicitud)

    return solicitud


# ============================================================
# REQUISITOS
# ============================================================


def obtener_requisito_solicitud_por_id(
    db: Session,
    id_solicitud_requisito: int,
) -> SolicitudRequisito | None:
    return db.get(
        SolicitudRequisito,
        id_solicitud_requisito,
    )


def actualizar_verificacion_requisito(
    db: Session,
    requisito: SolicitudRequisito,
    *,
    estado_verificacion: str,
    id_usuario_verificador: int,
    fecha_verificacion: datetime,
    detalle_verificacion: str | None,
) -> SolicitudRequisito:
    """
    Actualiza el resultado administrativo actual
    de un requisito.

    El service decide si corresponde una revisión manual
    o una validación mediante API.
    """
    requisito.estado_verificacion = (
        estado_verificacion
    )
    requisito.id_usuario_verificador = (
        id_usuario_verificador
    )
    requisito.fecha_verificacion = (
        fecha_verificacion
    )
    requisito.detalle_verificacion = (
        detalle_verificacion
    )

    db.flush()
    db.refresh(requisito)

    return requisito