"""Configuración lineal y condiciones de igualdad; nunca ejecuta expresiones."""
from pydantic import TypeAdapter, ValidationError

from app.repositories.gestion_seguimiento import tramite_repository, seguimiento_repository
from app.schemas.gestion_seguimiento.seguimiento import CondicionRequisito
from app.services.gestion_seguimiento.seguimiento_service import SeguimientoError


def validar_condicion(condicion, campos):
    if condicion is None:
        return None
    try:
        regla = TypeAdapter(CondicionRequisito).validate_python(condicion)
    except ValidationError as exc:
        raise SeguimientoError('La condición del requisito no es válida.', 400) from exc
    if regla.origen == 'solicitud_dato':
        campo = next((c for c in campos if c.activo and c.clave == regla.clave), None)
        if campo is None:
            raise SeguimientoError('La condición debe referenciar un campo activo del mismo trámite.', 400)
        # Reutiliza tipos, fechas y opciones del formulario, sin evaluar código.
        from app.services.gestion_seguimiento.solicitud_service import _validar_valor_campo, SolicitudServiceError
        try:
            regla.valor = _validar_valor_campo(campo, regla.valor)
        except SolicitudServiceError as exc:
            raise SeguimientoError(f'Valor de condición incompatible: {exc}', 400) from exc
    return regla


def igualdad_simple(actual, esperado):
    # JSON distingue false de 0 aunque Python los compare como iguales.
    if isinstance(actual, bool) != isinstance(esperado, bool):
        return False
    return actual == esperado


def requisitos_aplicables(db, solicitud, requisitos, campos, datos):
    valores = {c.clave: d.valor for c in campos for d in datos if c.id_campo == d.id_campo}
    perfil = seguimiento_repository.obtener_perfil(db, solicitud.id_solicitante)
    aplicables = []
    for requisito in requisitos:
        regla = validar_condicion(requisito.condicion, campos)
        if regla is None:
            aplicables.append(requisito)
            continue
        valor = valores.get(regla.clave) if regla.origen == 'solicitud_dato' else getattr(perfil, regla.campo, None)
        if valor is None:
            fuente = regla.clave if regla.origen == 'solicitud_dato' else regla.campo
            raise SeguimientoError(f'Completa {fuente} para determinar los requisitos aplicables.', 400)
        if igualdad_simple(valor, regla.valor):
            aplicables.append(requisito)
    return aplicables


def validar_flujo_envio(db, tramite):
    if tramite.tipo_finalizacion is None:
        raise SeguimientoError('El trámite todavía no tiene configurada su forma de finalización.')
    etapas = tramite_repository.listar_etapas_tramite(db, tramite.id_tramite, solo_activas=True)
    if not etapas or not etapas[0].es_inicial or not etapas[-1].es_final:
        raise SeguimientoError('El trámite debe tener un flujo activo con primera etapa inicial y última final.')
    if sum(e.es_inicial for e in etapas) != 1 or sum(e.es_final for e in etapas) != 1:
        raise SeguimientoError('El flujo debe tener una sola etapa inicial y una sola final.')
    ids = {e.id_etapa for e in etapas}
    requisitos = tramite_repository.listar_requisitos_tramite(db, tramite.id_tramite, solo_activos=True)
    if any(r.id_etapa is not None and r.id_etapa not in ids for r in requisitos):
        raise SeguimientoError('Un requisito activo referencia una etapa inactiva o de otro trámite.')
    return etapas
