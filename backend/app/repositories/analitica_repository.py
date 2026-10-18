# RETIRO_ENTREGA_FISICA_13F
"""Agregaciones de lectura. No carga solicitudes ni contenido de mensajes."""
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.chat.chat_message import ChatMessage
from app.models.gestion_seguimiento.solicitud import Solicitud
from app.models.gestion_seguimiento.solicitud_resultado import SolicitudResultado
from app.models.gestion_seguimiento.tramite import Tramite


def solicitudes_con_fecha_conclusion(id_tramite: int | None):
    """
    La conclusión administrativa se acredita al registrar
    el resultado del trámite.

    Para trámites de recojo:
        lista_para_entrega es terminal.

    Para otras modalidades:
        finalizada es terminal.

    No se requiere confirmar la entrega física.
    """

    resultado_valido = and_(
        SolicitudResultado.tipo_finalizacion
        == Solicitud.tipo_finalizacion,
        SolicitudResultado.fecha_registro
        >= Solicitud.fecha_creacion,
    )

    fecha = SolicitudResultado.fecha_registro

    stmt = (
        select(
            Solicitud.id_solicitud,
            Solicitud.fecha_creacion,
            fecha.label("conclusion"),
        )
        .outerjoin(
            SolicitudResultado,
            SolicitudResultado.id_solicitud
            == Solicitud.id_solicitud,
        )
        .where(
            resultado_valido,
            or_(
                Solicitud.estado == "finalizada",
                and_(
                    Solicitud.estado == "lista_para_entrega",
                    Solicitud.tipo_finalizacion == "entrega",
                ),
            ),
        )
    )

    if id_tramite is not None:
        stmt = stmt.where(
            Solicitud.id_tramite == id_tramite
        )

    return stmt.subquery()


def _periodo(columna, agrupacion, zona):
    return func.date_trunc(agrupacion, func.timezone(zona, columna))


def consultar_agregados(db: Session, *, desde, hasta, agrupacion, zona, id_tramite):
    """Seis consultas acotadas/agregadas; nunca commit ni escrituras.

    Las filas finalizadas sin fecha fiable se comprueban en todo el ámbito:
    sin esa fecha tampoco es posible determinar a qué período pertenecen.
    """
    opciones = db.execute(select(Tramite.id_tramite, Tramite.nombre)
                          .order_by(Tramite.nombre, Tramite.id_tramite)).mappings().all()
    filtros = [Solicitud.fecha_creacion >= desde, Solicitud.fecha_creacion < hasta]
    if id_tramite is not None:
        filtros.append(Solicitud.id_tramite == id_tramite)
    periodo = _periodo(Solicitud.fecha_creacion, agrupacion, zona)
    recibidas = db.execute(
        select(periodo.label('periodo'), func.count().label('cantidad'))
        .where(*filtros).group_by(periodo).order_by(periodo)
    ).mappings().all()

    finales = solicitudes_con_fecha_conclusion(id_tramite)
    en_periodo = and_(finales.c.conclusion >= desde, finales.c.conclusion < hasta)
    duracion_dias = func.extract('epoch', finales.c.conclusion - finales.c.fecha_creacion) / 86400.0
    resumen = db.execute(select(
        func.count().filter(en_periodo).label('concluidas'),
        func.percentile_cont(0.5).within_group(duracion_dias).filter(en_periodo).label('mediana'),
        func.count().filter(finales.c.conclusion.is_(None)).label('sin_fecha'),
    ).select_from(finales)).mappings().one()
    periodo_final = _periodo(finales.c.conclusion, agrupacion, zona)
    concluidas = db.execute(
        select(periodo_final.label('periodo'), func.count().label('cantidad'))
        .where(en_periodo).group_by(periodo_final).order_by(periodo_final)
    ).mappings().all()

    cantidad = func.count(Solicitud.id_solicitud)
    top = db.execute(
        select(Tramite.id_tramite, Tramite.nombre, cantidad.label('cantidad'))
        .join(Solicitud, Solicitud.id_tramite == Tramite.id_tramite)
        .where(*filtros).group_by(Tramite.id_tramite, Tramite.nombre)
        .order_by(cantidad.desc(), Tramite.id_tramite).limit(5)
    ).mappings().all()

    periodo_rag = _periodo(ChatMessage.created_at, agrupacion, zona)
    rag = db.execute(
        select(periodo_rag.label('periodo'), func.count().label('cantidad'))
        .where(ChatMessage.role == 'user', ChatMessage.created_at >= desde,
               ChatMessage.created_at < hasta)
        .group_by(periodo_rag).order_by(periodo_rag)
    ).mappings().all()
    return dict(tramites=opciones, recibidas=recibidas, resumen=resumen,
                concluidas=concluidas, top=top, rag=rag)
