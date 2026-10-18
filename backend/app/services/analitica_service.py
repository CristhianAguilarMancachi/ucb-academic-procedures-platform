from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.repositories import analitica_repository as repo
from app.schemas.analitica import AnaliticaResponse, FiltrosAnalitica


ZONA = 'America/La_Paz'


class TramiteAnaliticaNoEncontrado(ValueError):
    pass


def resolver_periodo(periodo, ahora=None):
    ahora = ahora or datetime.now(ZoneInfo(ZONA))
    if ahora.tzinfo is None:
        raise ValueError('La fecha de referencia debe incluir zona horaria.')
    hasta = ahora.astimezone(ZoneInfo(ZONA))
    hoy = hasta.date()
    if periodo in ('30_dias', '90_dias'):
        inicio = hoy - timedelta(days=29 if periodo == '30_dias' else 89)
        agrupacion = 'week'
    elif periodo == '12_meses':
        # Doce meses calendario, incluyendo el mes actual hasta ahora.
        mes = hoy.year * 12 + hoy.month - 1 - 11
        inicio = hoy.replace(year=mes // 12, month=mes % 12 + 1, day=1)
        agrupacion = 'month'
    else:
        raise ValueError('Período no admitido.')
    return datetime.combine(inicio, time.min, ZoneInfo(ZONA)), hasta, agrupacion


def periodos_serie(desde, hasta, agrupacion):
    fecha = desde.date()
    fecha = fecha - timedelta(days=fecha.weekday()) if agrupacion == 'week' else fecha.replace(day=1)
    while fecha <= hasta.date():
        yield fecha
        if agrupacion == 'week':
            fecha += timedelta(days=7)
        else:
            fecha = (fecha.replace(day=28) + timedelta(days=4)).replace(day=1)


def obtener_analitica(db, filtros: FiltrosAnalitica, *, ahora=None) -> AnaliticaResponse:
    desde, hasta, agrupacion = resolver_periodo(filtros.periodo, ahora)
    datos = repo.consultar_agregados(db, desde=desde, hasta=hasta, agrupacion=agrupacion,
                                    zona=ZONA, id_tramite=filtros.id_tramite)
    if filtros.id_tramite is not None and not any(
        t['id_tramite'] == filtros.id_tramite for t in datos['tramites']
    ):
        raise TramiteAnaliticaNoEncontrado('El trámite seleccionado no existe.')
    recibidas, concluidas, rag = (
        {fila['periodo'].date(): fila['cantidad'] for fila in datos[serie]}
        for serie in ('recibidas', 'concluidas', 'rag')
    )
    resumen = datos['resumen']
    fechas_fiables = resumen['sin_fecha'] == 0
    limitaciones = [
        'El RAG no persiste la identidad del consultante: no se puede distinguir autenticados y visitantes.',
        'Las consultas RAG cuentan mensajes de usuario conservados; preguntas no persistidas o eliminadas no son recuperables.',
    ]
    if not fechas_fiables:
        limitaciones.append(
            'Existen solicitudes finalizadas sin una fecha de conclusión fiable en el ámbito seleccionado. '
            'No es posible asignarlas a un período: el conteo, la mediana y la serie de conclusiones no están disponibles.'
        )
    return AnaliticaResponse(
        filtros=filtros, desde=desde, hasta=hasta, zona_horaria=ZONA,
        agrupacion='semana' if agrupacion == 'week' else 'mes',
        indicadores=dict(solicitudes_recibidas=sum(recibidas.values()),
                         solicitudes_concluidas=resumen['concluidas'] if fechas_fiables else None,
                         tiempo_mediano_dias=resumen['mediana'] if fechas_fiables else None,
                         consultas_rag=sum(rag.values())),
        evolucion_solicitudes=[dict(periodo=p, recibidas=recibidas.get(p, 0),
                                    concluidas=concluidas.get(p, 0) if fechas_fiables else None)
                               for p in periodos_serie(desde, hasta, agrupacion)],
        top_tramites=datos['top'],
        evolucion_rag=[dict(periodo=p, consultas=rag.get(p, 0))
                       for p in periodos_serie(desde, hasta, agrupacion)],
        tramites=datos['tramites'], limitaciones=limitaciones,
    )
