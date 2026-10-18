
"""Validación de requisitos condicionales y modalidad del trámite."""

from pydantic import TypeAdapter, ValidationError

from app.repositories.gestion_seguimiento import seguimiento_repository
from app.schemas.gestion_seguimiento.seguimiento import CondicionRequisito
from app.services.gestion_seguimiento.seguimiento_service import SeguimientoError


def validar_condicion(condicion, campos):
    if condicion is None:
        return None

    try:
        regla = TypeAdapter(CondicionRequisito).validate_python(condicion)
    except ValidationError as exc:
        raise SeguimientoError(
            "La condición del requisito no es válida.", 400
        ) from exc

    if regla.origen == "solicitud_dato":
        campo = next(
            (c for c in campos if c.activo and c.clave == regla.clave),
            None,
        )
        if campo is None:
            raise SeguimientoError(
                "La condición debe referenciar un campo activo del mismo trámite.",
                400,
            )

        from app.services.gestion_seguimiento.solicitud_service import (
            SolicitudServiceError,
            _validar_valor_campo,
        )

        try:
            regla.valor = _validar_valor_campo(campo, regla.valor)
        except SolicitudServiceError as exc:
            raise SeguimientoError(
                f"Valor de condición incompatible: {exc}", 400
            ) from exc

    return regla


def igualdad_simple(actual, esperado):
    # JSON distingue false de 0, aunque Python los compare como iguales.
    if isinstance(actual, bool) != isinstance(esperado, bool):
        return False
    return actual == esperado


def requisitos_aplicables(db, solicitud, requisitos, campos, datos):
    valores = {
        campo.clave: dato.valor
        for campo in campos
        for dato in datos
        if campo.id_campo == dato.id_campo
    }

    perfil = seguimiento_repository.obtener_perfil(
        db, solicitud.id_solicitante
    )
    aplicables = []

    for requisito in requisitos:
        regla = validar_condicion(requisito.condicion, campos)

        if regla is None:
            aplicables.append(requisito)
            continue

        if regla.origen == "solicitud_dato":
            valor = valores.get(regla.clave)
            fuente = regla.clave
        else:
            valor = getattr(perfil, regla.campo, None)
            fuente = regla.campo

        if valor is None:
            raise SeguimientoError(
                f"Completa {fuente} para determinar los requisitos aplicables.",
                400,
            )

        if igualdad_simple(valor, regla.valor):
            aplicables.append(requisito)

    return aplicables


def validar_flujo_envio(db, tramite) -> None:
    """
    Comprueba la configuración necesaria para enviar una
    solicitud sin exigir etapas administrativas internas.
    """

    if tramite.tipo_finalizacion not in {
        "entrega",
        "resultado_registrado",
        "externo",
    }:
        raise SeguimientoError(
            "El trámite no tiene una forma de finalización válida."
        )

    tipo = tramite.tipo_intervencion

    if tipo not in {"ninguna", "firma", "conformidad"}:
        raise SeguimientoError(
            "El tipo de intervención del trámite no es válido."
        )

    if (
        tipo != "ninguna"
        and tramite.tipo_finalizacion != "resultado_registrado"
    ):
        raise SeguimientoError(
            "Las intervenciones presenciales requieren finalización "
            "por resultado registrado."
        )
