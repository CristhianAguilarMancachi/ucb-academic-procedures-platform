from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento import (
    pago_verificacion_repository,
    solicitud_administrativa_repository,
)
from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoApiRespuesta,
    PagoApiValidarRequest,
    PagoVerificacionResultadoResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)


class PagoVerificacionServiceError(
    Exception
):
    """Error base del servicio de verificación de pagos."""


class RequisitoPagoNoEncontradoError(
    PagoVerificacionServiceError
):
    """El requisito indicado no existe."""


class SolicitudPagoNoEncontradaError(
    PagoVerificacionServiceError
):
    """La solicitud no existe para gestión administrativa."""


class SolicitudPagoNoEstaEnRevisionError(
    PagoVerificacionServiceError
):
    """La solicitud aún no puede verificar pagos."""


class RequisitoNoPerteneceSolicitudPagoError(
    PagoVerificacionServiceError
):
    """El requisito no pertenece a la solicitud."""


class RequisitoNoEconomicoError(
    PagoVerificacionServiceError
):
    """El requisito no corresponde a un concepto económico."""


class InformacionPagoIncompletaError(
    PagoVerificacionServiceError
):
    """Falta información necesaria para consultar la API."""


class FacturaYaUtilizadaError(
    PagoVerificacionServiceError
):
    """La factura ya acreditó otro requisito."""


class PagoApiNoDisponibleError(
    PagoVerificacionServiceError
):
    """No fue posible consultar correctamente la API."""


# ============================================================
# CLIENTE EXTERNO
# ============================================================


def _consultar_api_pago(
    datos: PagoApiValidarRequest,
) -> PagoApiRespuesta:
    """
    La implementación HTTP real se encuentra aislada en
    pago_api_client.py.

    El import se realiza aquí para mantener desacoplado
    este service del transporte HTTP.
    """
    from app.services.gestion_seguimiento.pago_api_client import (
        validar_factura,
    )

    return validar_factura(
        datos
    )


# ============================================================
# HELPERS
# ============================================================


def _crear_resultado(
    verificacion,
    *,
    mensaje: str,
) -> PagoVerificacionResultadoResponse:
    return PagoVerificacionResultadoResponse(
        id_verificacion_pago=(
            verificacion.id_verificacion_pago
        ),
        id_solicitud_requisito=(
            verificacion.id_solicitud_requisito
        ),
        numero_factura_consultado=(
            verificacion.numero_factura_consultado
        ),
        codigo_concepto_consultado=(
            verificacion.codigo_concepto_consultado
        ),
        codigo_concepto_reportado=(
            verificacion.codigo_concepto_reportado
        ),
        estado_factura_reportado=(
            verificacion.estado_factura_reportado
        ),
        monto_reportado=(
            verificacion.monto_reportado
        ),
        moneda_reportada=(
            verificacion.moneda_reportada
        ),
        estado=verificacion.estado,
        fecha_verificacion=(
            verificacion.fecha_verificacion
        ),
        mensaje=mensaje,
    )


def _normalizar_moneda(
    moneda: str | None,
) -> str | None:
    if moneda is None:
        return None

    return moneda.strip().upper()


def _evaluar_respuesta_api(
    *,
    respuesta: PagoApiRespuesta,
    numero_factura_esperado: str,
    codigo_esperado: str,
    monto_esperado: Decimal,
    moneda_esperada: str,
) -> tuple[bool, str]:
    """
    El sistema toma la decisión final.

    La API informa hechos sobre la factura.
    Nuestro backend compara esos hechos contra el snapshot
    de la solicitud.
    """
    if not respuesta.encontrada:
        return (
            False,
            "La factura no fue encontrada.",
        )

    if (
        respuesta.numero_factura.strip()
        != numero_factura_esperado
    ):
        return (
            False,
            "El número de factura reportado por la API "
            "no coincide con el consultado.",
        )

    if respuesta.utilizada is True:
        return (
            False,
            "La API reporta que la factura ya fue utilizada.",
        )

    if respuesta.codigo is None:
        return (
            False,
            "La API no reportó el código del concepto.",
        )

    if (
        respuesta.codigo.strip()
        != codigo_esperado
    ):
        return (
            False,
            "La factura no corresponde al concepto "
            "económico esperado.",
        )

    if respuesta.monto is None:
        return (
            False,
            "La API no reportó el monto de la factura.",
        )

    if respuesta.monto != monto_esperado:
        return (
            False,
            "El monto reportado por la factura no coincide "
            "con el monto esperado.",
        )

    moneda_reportada = _normalizar_moneda(
        respuesta.moneda
    )

    if moneda_reportada is None:
        return (
            False,
            "La API no reportó la moneda de la factura.",
        )

    if moneda_reportada != _normalizar_moneda(
        moneda_esperada
    ):
        return (
            False,
            "La moneda reportada por la factura no coincide "
            "con la moneda esperada.",
        )

    if respuesta.estado_factura is None:
        return (
            False,
            "La API no reportó el estado de la factura.",
        )

    if (
        respuesta.estado_factura.strip().lower()
        != "pagada"
    ):
        return (
            False,
            "La factura no se encuentra en estado pagada.",
        )

    return (
        True,
        "La factura fue verificada correctamente.",
    )


# ============================================================
# VERIFICACIÓN DE PAGO
# ============================================================


def verificar_pago_requisito(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitud_requisito: int,
    id_usuario_verificador: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> PagoVerificacionResultadoResponse:
    """
    Valida mediante API el pago asociado a un requisito.

    Flujo:
    1. comprueba solicitud;
    2. comprueba requisito;
    3. obtiene factura y código desde el snapshot;
    4. impide reutilización interna;
    5. consulta API;
    6. compara respuesta con monto/código/moneda esperados;
    7. registra el intento;
    8. actualiza el requisito.

    No cambia etapa ni unidad de la solicitud.
    """
    solicitud = (
        solicitud_administrativa_repository
        .obtener_solicitud_administrativa_por_id(
            db,
            id_solicitud,
        )
    )

    if solicitud is None:
        raise SolicitudPagoNoEncontradaError(
            "La solicitud no existe o no está disponible "
            "para gestión administrativa."
        )

    if solicitud.estado != "en_revision":
        raise SolicitudPagoNoEstaEnRevisionError(
            "La solicitud debe estar en revisión "
            "antes de verificar el pago."
        )

    requisito = (
        solicitud_administrativa_repository
        .obtener_requisito_solicitud_por_id(
            db,
            id_solicitud_requisito,
        )
    )

    if requisito is None:
        raise RequisitoPagoNoEncontradoError(
            "El requisito indicado no existe."
        )

    if requisito.id_solicitud != id_solicitud:
        raise RequisitoNoPerteneceSolicitudPagoError(
            "El requisito no pertenece a la solicitud."
        )

    if not requisito.es_economico:
        raise RequisitoNoEconomicoError(
            "El requisito indicado no es económico."
        )

    numero_factura = (
        requisito.numero_factura.strip()
        if requisito.numero_factura is not None
        else None
    )

    codigo_concepto = (
        requisito.codigo_concepto_externo.strip()
        if requisito.codigo_concepto_externo is not None
        else None
    )

    if numero_factura is None:
        raise InformacionPagoIncompletaError(
            "El requisito no tiene un número de factura "
            "registrado."
        )

    if codigo_concepto is None:
        raise InformacionPagoIncompletaError(
            "El requisito no tiene código de concepto "
            "externo configurado."
        )

    if requisito.monto_economico is None:
        raise InformacionPagoIncompletaError(
            "El requisito no tiene monto económico "
            "registrado."
        )

    if requisito.moneda is None:
        raise InformacionPagoIncompletaError(
            "El requisito no tiene moneda registrada."
        )

    # ========================================================
    # PROTECCIÓN CONTRA REUTILIZACIÓN
    # ========================================================

    verificacion_anterior = (
        pago_verificacion_repository
        .obtener_verificacion_exitosa_por_factura(
            db,
            numero_factura,
        )
    )

    if verificacion_anterior is not None:
        if (
            verificacion_anterior.id_solicitud_requisito
            == requisito.id_solicitud_requisito
        ):
            return _crear_resultado(
                verificacion_anterior,
                mensaje=(
                    "La factura ya fue verificada "
                    "correctamente para este requisito."
                ),
            )

        raise FacturaYaUtilizadaError(
            "El número de factura ya fue utilizado "
            "para acreditar otra solicitud."
        )

    request_api = PagoApiValidarRequest(
        codigo=codigo_concepto,
        numero_factura=numero_factura,
    )

    # ========================================================
    # CONSULTA API
    # ========================================================

    try:
        respuesta_api = _consultar_api_pago(
            request_api
        )

    except Exception as exc:
        try:
            verificacion_error = (
                pago_verificacion_repository
                .crear_verificacion_pago(
                    db,
                    id_solicitud_requisito=(
                        requisito.id_solicitud_requisito
                    ),
                    id_usuario_verificador=(
                        id_usuario_verificador
                    ),
                    numero_factura_consultado=(
                        numero_factura
                    ),
                    codigo_concepto_consultado=(
                        codigo_concepto
                    ),
                    estado="error",
                    detalle_respuesta={
                        "tipo": "error_api",
                    },
                )
            )

            registrar_accion_simple(
                db,
                accion="verificar_pago_api_error",
                modulo="gestion_seguimiento",
                id_usuario_actor=(
                    id_usuario_verificador
                ),
                entidad="solicitud_requisito",
                id_entidad=str(
                    requisito.id_solicitud_requisito
                ),
                exitoso=False,
                detalle={
                    "id_solicitud": id_solicitud,
                },
                direccion_ip=direccion_ip,
                user_agent=user_agent,
            )

            db.commit()

            return _crear_resultado(
                verificacion_error,
                mensaje=(
                    "No fue posible consultar la API "
                    "de pagos. El requisito permanece "
                    "pendiente."
                ),
            )

        except Exception:
            db.rollback()
            raise PagoApiNoDisponibleError(
                "No fue posible consultar la API "
                "de pagos."
            ) from exc

    # ========================================================
    # COMPARACIÓN
    # ========================================================

    verificado, mensaje = (
        _evaluar_respuesta_api(
            respuesta=respuesta_api,
            numero_factura_esperado=(
                numero_factura
            ),
            codigo_esperado=(
                codigo_concepto
            ),
            monto_esperado=(
                requisito.monto_economico
            ),
            moneda_esperada=(
                requisito.moneda
            ),
        )
    )

    estado_verificacion_pago = (
        "verificado"
        if verificado
        else "no_verificado"
    )

    estado_requisito = (
        "cumple"
        if verificado
        else "no_cumple"
    )

    fecha_verificacion = datetime.now(
        timezone.utc
    )

    detalle_respuesta = (
        respuesta_api.model_dump(
            mode="json"
        )
    )

    try:
        registro = (
            pago_verificacion_repository
            .crear_verificacion_pago(
                db,
                id_solicitud_requisito=(
                    requisito.id_solicitud_requisito
                ),
                id_usuario_verificador=(
                    id_usuario_verificador
                ),
                numero_factura_consultado=(
                    numero_factura
                ),
                codigo_concepto_consultado=(
                    codigo_concepto
                ),
                codigo_concepto_reportado=(
                    respuesta_api.codigo
                ),
                estado_factura_reportado=(
                    respuesta_api.estado_factura
                ),
                monto_reportado=(
                    respuesta_api.monto
                ),
                moneda_reportada=(
                    _normalizar_moneda(
                        respuesta_api.moneda
                    )
                ),
                estado=(
                    estado_verificacion_pago
                ),
                detalle_respuesta=(
                    detalle_respuesta
                ),
            )
        )

        solicitud_administrativa_repository.actualizar_verificacion_requisito(
            db,
            requisito,
            estado_verificacion=(
                estado_requisito
            ),
            id_usuario_verificador=(
                id_usuario_verificador
            ),
            fecha_verificacion=(
                fecha_verificacion
            ),
            detalle_verificacion=(
                mensaje
            ),
        )

        registrar_accion_simple(
            db,
            accion="verificar_pago_solicitud",
            modulo="gestion_seguimiento",
            id_usuario_actor=(
                id_usuario_verificador
            ),
            entidad="solicitud_requisito",
            id_entidad=str(
                requisito.id_solicitud_requisito
            ),
            exitoso=verificado,
            detalle={
                "id_solicitud": id_solicitud,
                "resultado": (
                    estado_verificacion_pago
                ),
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        return _crear_resultado(
            registro,
            mensaje=mensaje,
        )

    except IntegrityError as exc:
        db.rollback()

        raise FacturaYaUtilizadaError(
            "El número de factura ya fue utilizado "
            "para acreditar otra solicitud."
        ) from exc

    except Exception:
        db.rollback()
        raise