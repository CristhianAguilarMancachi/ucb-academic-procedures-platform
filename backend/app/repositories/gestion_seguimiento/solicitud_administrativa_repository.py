from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.gestion_seguimiento.perfil_academico import (
    PerfilAcademico,
)
from app.models.gestion_seguimiento.solicitud import Solicitud
from app.models.gestion_seguimiento.solicitud_recepcion import (
    SolicitudRecepcion,
)
from app.models.gestion_seguimiento.solicitud_requisito import (
    SolicitudRequisito,
)
from app.models.gestion_seguimiento.tramite import Tramite
from app.models.usuario import Usuario


# ============================================================
# BANDEJA ADMINISTRATIVA
# ============================================================


def listar_solicitudes_administrativas(
    db: Session,
    *,
    estado: str | None = None,
    id_tramite: int | None = None,
    estado_pago: str | None = None,
    vista: str = "todas",
    orden: str = "prioridad",
    id_solicitud: int | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    id_solicitante: int | None = None,
    busqueda: str | None = None,
    pagina: int = 1,
    limite: int = 20,
) -> tuple[Sequence[Solicitud], int]:
    """
    Lista solicitudes visibles para gestión administrativa.

    Permite buscar globalmente por:
    - número de solicitud;
    - nombre o apellido del solicitante;
    - nombre completo;
    - documento de identidad / CI;
    - nombre del trámite.

    La búsqueda se realiza antes de la paginación.
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
        Solicitud.fecha_envio.is_not(None),
    ]

    estados_activos = (
        "pendiente_recepcion",
        "en_revision",
        "en_proceso",
    )

    estados_finalizados = (
        "lista_para_entrega",
        "finalizada",
        "rechazada",
        "cancelada",
    )

    if vista == "por_atender":
        filtros.append(Solicitud.estado.in_(estados_activos))
    elif vista == "finalizadas":
        filtros.append(Solicitud.estado.in_(estados_finalizados))

    requisito_economico = (
        SolicitudRequisito.concepto_economico.is_not(None)
    )

    requisito_sin_verificar = and_(
        SolicitudRequisito.concepto_economico.is_not(None),
        SolicitudRequisito.estado_verificacion != "cumple",
    )

    if estado_pago == "no_aplica":
        filtros.append(
            ~Solicitud.requisitos.any(requisito_economico)
        )
    elif estado_pago == "verificado":
        filtros.extend([
            Solicitud.requisitos.any(requisito_economico),
            ~Solicitud.requisitos.any(requisito_sin_verificar),
        ])
    elif estado_pago == "pendiente":
        filtros.append(
            Solicitud.requisitos.any(requisito_sin_verificar)
        )

    if id_solicitante is not None:
        filtros.append(
            Solicitud.id_solicitante
            == id_solicitante
        )

    zona = ZoneInfo(
        "America/La_Paz"
    )

    if fecha_desde:
        filtros.append(
            Solicitud.fecha_envio
            >= datetime.combine(
                fecha_desde,
                time.min,
                zona,
            )
        )

    if fecha_hasta:
        filtros.append(
            Solicitud.fecha_envio
            < datetime.combine(
                fecha_hasta
                + timedelta(days=1),
                time.min,
                zona,
            )
        )

    if estado == "finalizada":
        filtros.append(
            Solicitud.estado.in_(
                ("finalizada", "lista_para_entrega")
            )
        )
    elif estado is not None:
        filtros.append(
            Solicitud.estado == estado
        )

    if id_tramite is not None:
        filtros.append(
            Solicitud.id_tramite
            == id_tramite
        )

    if id_solicitud is not None:
        filtros.append(
            Solicitud.id_solicitud
            == id_solicitud
        )

    busqueda_normalizada = (
        busqueda.strip()
        if busqueda
        else ""
    )

    if busqueda_normalizada:
        patron = (
            f"%{busqueda_normalizada}%"
        )

        nombre_completo = func.concat_ws(
            " ",
            Usuario.nombres,
            Usuario.apellidos,
        )

        filtros.append(
            or_(
                cast(
                    Solicitud.id_solicitud,
                    String,
                ).ilike(patron),

                Usuario.nombres.ilike(
                    patron
                ),

                Usuario.apellidos.ilike(
                    patron
                ),

                nombre_completo.ilike(
                    patron
                ),

                PerfilAcademico
                .documento_identidad
                .ilike(patron),

                Solicitud
                .nombre_tramite_snapshot
                .ilike(patron),

                Tramite.nombre.ilike(
                    patron
                ),
            )
        )

    consulta_base = (
        select(Solicitud)
        .join(
            Usuario,
            Usuario.id_usuario
            == Solicitud.id_solicitante,
        )
        .join(
            Tramite,
            Tramite.id_tramite
            == Solicitud.id_tramite,
        )
        .outerjoin(
            PerfilAcademico,
            PerfilAcademico.id_usuario
            == Solicitud.id_solicitante,
        )
        .where(
            *filtros
        )
    )

    total = (
        db.scalar(
            select(
                func.count(
                    Solicitud.id_solicitud
                )
            )
            .join(
                Usuario,
                Usuario.id_usuario
                == Solicitud.id_solicitante,
            )
            .join(
                Tramite,
                Tramite.id_tramite
                == Solicitud.id_tramite,
            )
            .outerjoin(
                PerfilAcademico,
                PerfilAcademico.id_usuario
                == Solicitud.id_solicitante,
            )
            .where(
                *filtros
            )
        )
        or 0
    )

    prioridad = case(
        (Solicitud.estado == "pendiente_recepcion", 0),
        (Solicitud.estado == "en_revision", 1),
        (Solicitud.estado == "en_proceso", 2),
        (Solicitud.estado == "lista_para_entrega", 3),
        (Solicitud.estado == "finalizada", 4),
        (Solicitud.estado == "rechazada", 5),
        (Solicitud.estado == "cancelada", 6),
        else_=7,
    )

    if orden == "recientes":
        criterio_orden = (
            Solicitud.fecha_envio.desc(),
            Solicitud.id_solicitud.desc(),
        )
    elif orden == "antiguos":
        criterio_orden = (
            Solicitud.fecha_envio.asc(),
            Solicitud.id_solicitud.asc(),
        )
    else:
        fecha_activa = case(
            (Solicitud.estado.in_(estados_activos), Solicitud.fecha_envio),
            else_=None,
        )
        fecha_cerrada = case(
            (Solicitud.estado.in_(estados_activos), None),
            else_=Solicitud.fecha_envio,
        )
        criterio_orden = (
            prioridad.asc(),
            fecha_activa.asc().nulls_last(),
            fecha_cerrada.desc().nulls_last(),
            Solicitud.id_solicitud.asc(),
        )

    consulta = (
        consulta_base
        .options(
            selectinload(
                Solicitud.tramite
            ),
            selectinload(
                Solicitud.solicitante
            ),
            selectinload(
                Solicitud.requisitos
            ),
            selectinload(
                Solicitud.datos
            ),
        )
        .order_by(*criterio_orden)
        .offset(
            (pagina - 1)
            * limite
        )
        .limit(
            limite
        )
    )

    solicitudes = (
        db.scalars(
            consulta
        )
        .unique()
        .all()
    )

    return (
        solicitudes,
        int(total),
    )


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
            Solicitud.id_solicitud
            == id_solicitud,
            Solicitud.fecha_envio.is_not(
                None
            ),
        )
        .options(
            selectinload(
                Solicitud.tramite
            ),
            selectinload(
                Solicitud.solicitante
            ),
            selectinload(
                Solicitud.datos
            ),
            selectinload(
                Solicitud.requisitos
            ),
        )
    )

    return (
        db.scalars(
            consulta
        )
        .unique()
        .one_or_none()
    )


# ============================================================
# RECEPCIÓN
# ============================================================


def obtener_recepcion_por_solicitud(
    db: Session,
    id_solicitud: int,
) -> SolicitudRecepcion | None:
    consulta = (
        select(
            SolicitudRecepcion
        )
        .where(
            SolicitudRecepcion.id_solicitud
            == id_solicitud
        )
    )

    return (
        db.scalars(
            consulta
        )
        .one_or_none()
    )


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
        id_usuario_receptor=(
            id_usuario_receptor
        ),
        fecha_recepcion=(
            fecha_recepcion
        ),
    )

    db.add(
        recepcion
    )

    db.flush()

    db.refresh(
        recepcion
    )

    return recepcion


def marcar_solicitud_en_revision(
    db: Session,
    solicitud: Solicitud,
) -> Solicitud:
    """
    Cambia pendiente_recepcion a en_revision.

    Esto NO representa el inicio de una etapa institucional.
    """
    solicitud.estado = (
        "en_revision"
    )

    db.flush()

    db.refresh(
        solicitud
    )

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

    db.refresh(
        requisito
    )

    return requisito