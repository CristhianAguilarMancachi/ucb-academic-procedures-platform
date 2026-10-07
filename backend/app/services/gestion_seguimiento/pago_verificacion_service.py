from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal

from sqlalchemy.exc import (
    IntegrityError,
)
from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento import (
    pago_verificacion_repository,
    solicitud_administrativa_repository,
)
from app.repositories.gestion_seguimiento import (
    seguimiento_repository as seguimiento_repo,
)
from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoApiRespuesta,
    PagoApiValidarRequest,
    PagoVerificacionResultadoResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)
from app.services.gestion_seguimiento.datos_pago_service import (
    obtener_documento_pago,
)
from app.services.gestion_seguimiento.seguimiento_service import (
    validar_requisito_editable,
)


class PagoVerificacionServiceError(Exception):
    """Error base del servicio de verificación de pagos."""


class RequisitoPagoNoEncontradoError(
    PagoVerificacionServiceError
):
    """El requisito indicado no existe."""


class SolicitudPagoNoEncontradaError(
    PagoVerificacionServiceError
):
    """La solicitud no existe o no está disponible."""


class SolicitudPagoNoEstaEnRevisionError(
    PagoVerificacionServiceError
):
    """El pago no puede gestionarse en el estado actual."""


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

        estado=(
            verificacion.estado
        ),

        fecha_verificacion=(
            verificacion.fecha_verificacion
        ),

        mensaje=(
            mensaje
        ),
    )


def _normalizar_moneda(
    moneda: str | None,
) -> str | None:
    if moneda is None:
        return None

    return (
        moneda
        .strip()
        .upper()
    )


def _datos_reportados_almacenables(
    respuesta: PagoApiRespuesta,
) -> dict:
    def texto(
        valor,
        limite,
        longitud_exacta=None,
    ):
        if valor is None:
            return None

        valor = valor.strip()

        if (
            not valor
            or len(
                valor
            ) > limite
            or (
                longitud_exacta
                and len(
                    valor
                )
                != longitud_exacta
            )
        ):
            return None

        return valor

    monto = (
        respuesta.monto
    )

    if (
        monto is not None
        and (
            not monto.is_finite()
            or monto <= 0
            or monto
            > Decimal(
                "9999999999.99"
            )
        )
    ):
        monto = None

    if (
        monto is not None
        and monto
        != monto.quantize(
            Decimal(
                "0.01"
            )
        )
    ):
        monto = None

    return {
        "codigo_concepto_reportado":
            texto(
                respuesta.codigo,
                100,
            ),

        "estado_factura_reportado":
            texto(
                respuesta.estado_factura,
                50,
            ),

        "monto_reportado":
            monto,

        "moneda_reportada":
            texto(
                _normalizar_moneda(
                    respuesta.moneda
                ),
                3,
                3,
            ),
    }


def _evaluar_respuesta_api(
    *,
    respuesta: PagoApiRespuesta,
    numero_factura_esperado: str,
    codigo_esperado: str,
    documento_esperado: str,
    monto_esperado: Decimal,
    moneda_esperada: str,
) -> tuple[
    bool,
    str,
]:
    if (
        not respuesta.encontrada
    ):
        return (
            False,
            "La factura no fue encontrada.",
        )

    if (
        respuesta.numero_factura
        .strip()
        != numero_factura_esperado
    ):
        return (
            False,
            "El número de factura reportado "
            "no coincide con el consultado.",
        )

    if (
        (
            respuesta.documento_identidad
            or ""
        ).strip()
        != documento_esperado
    ):
        return (
            False,
            "La cédula de identidad del pago "
            "no coincide.",
        )

    if (
        respuesta.utilizada
        is True
    ):
        return (
            False,
            "La factura ya fue utilizada.",
        )

    if (
        respuesta.codigo
        is None
    ):
        return (
            False,
            "La API no reportó el código "
            "del concepto.",
        )

    if (
        respuesta.codigo
        .strip()
        != codigo_esperado
    ):
        return (
            False,
            "La factura no corresponde al "
            "concepto económico esperado.",
        )

    if (
        respuesta.monto
        is None
    ):
        return (
            False,
            "La API no reportó el monto "
            "de la factura.",
        )

    if (
        respuesta.monto
        != monto_esperado
    ):
        return (
            False,
            "El monto reportado por la factura "
            "no coincide con el monto esperado.",
        )

    moneda_reportada = (
        _normalizar_moneda(
            respuesta.moneda
        )
    )

    if (
        moneda_reportada
        is None
    ):
        return (
            False,
            "La API no reportó la moneda "
            "de la factura.",
        )

    if (
        moneda_reportada
        != _normalizar_moneda(
            moneda_esperada
        )
    ):
        return (
            False,
            "La moneda reportada por la factura "
            "no coincide con la moneda esperada.",
        )

    if (
        respuesta.estado_factura
        is None
    ):
        return (
            False,
            "La API no reportó el estado "
            "de la factura.",
        )

    if (
        respuesta.estado_factura
        .strip()
        .lower()
        != "pagada"
    ):
        return (
            False,
            "La factura todavía no figura "
            "como pagada.",
        )

    return (
        True,
        "La factura fue verificada correctamente.",
    )


def _validar_requisito_basico(
    solicitud,
    requisito,
    *,
    id_solicitud: int,
) -> None:
    if requisito is None:
        raise RequisitoPagoNoEncontradoError(
            "El requisito indicado no existe."
        )

    if (
        requisito.id_solicitud
        != id_solicitud
    ):
        raise RequisitoNoPerteneceSolicitudPagoError(
            "El requisito no pertenece "
            "a la solicitud."
        )

    if (
        not requisito.es_economico
    ):
        raise RequisitoNoEconomicoError(
            "El requisito indicado "
            "no es económico."
        )


def _validar_disponibilidad_solicitante(
    solicitud,
    requisito,
) -> None:
    if (
        solicitud.estado
        not in {
            "pendiente_recepcion",
            "en_revision",
            "en_proceso",
        }
    ):
        raise SolicitudPagoNoEstaEnRevisionError(
            "El pago no puede verificarse "
            "en el estado actual de la solicitud."
        )

    if (
        requisito.id_solicitud_etapa
        is not None
        and (
            solicitud.estado
            != "en_proceso"
            or requisito.id_solicitud_etapa
            != solicitud.id_etapa_actual
        )
    ):
        raise SolicitudPagoNoEstaEnRevisionError(
            "El pago se habilitará cuando "
            "la solicitud llegue a la etapa correspondiente."
        )


# ============================================================
# NÚCLEO DE VERIFICACIÓN
# ============================================================


def _verificar_pago(
    db: Session,
    *,
    solicitud,
    requisito,
    id_usuario_verificador: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> PagoVerificacionResultadoResponse:
    numero_factura = (
        requisito.numero_factura.strip()
        if (
            requisito.numero_factura
            is not None
        )
        else None
    )

    codigo_concepto = (
        requisito.codigo_concepto_externo
        .strip()
        if (
            requisito.codigo_concepto_externo
            is not None
        )
        else None
    )

    if not numero_factura:
        raise InformacionPagoIncompletaError(
            "El requisito no tiene un "
            "número de factura registrado."
        )

    if not codigo_concepto:
        raise InformacionPagoIncompletaError(
            "El requisito no tiene código "
            "de servicio externo configurado."
        )

    if (
        requisito.monto_economico
        is None
    ):
        raise InformacionPagoIncompletaError(
            "El requisito no tiene monto "
            "económico registrado."
        )

    if (
        requisito.moneda
        is None
    ):
        raise InformacionPagoIncompletaError(
            "El requisito no tiene moneda registrada."
        )

    # ========================================================
    # FACTURA YA VERIFICADA
    # ========================================================

    verificacion_anterior = (
        pago_verificacion_repository
        .obtener_verificacion_exitosa_por_factura(
            db,
            numero_factura,
        )
    )

    if (
        verificacion_anterior
        is not None
    ):
        if (
            verificacion_anterior
            .id_solicitud_requisito
            ==
            requisito
            .id_solicitud_requisito
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

    # ========================================================
    # CI
    # ========================================================

    documento = (
        obtener_documento_pago(
            db,
            solicitud,
        )
    )

    if not documento:
        raise InformacionPagoIncompletaError(
            "El solicitante debe registrar "
            "su documento de identidad "
            "para verificar el pago."
        )

    request_api = (
        PagoApiValidarRequest(
            documento_identidad=(
                documento
            ),

            codigo=(
                codigo_concepto
            ),

            numero_factura=(
                numero_factura
            ),
        )
    )

    # ========================================================
    # CONSULTA A API
    # ========================================================

    try:
        respuesta_api = (
            _consultar_api_pago(
                request_api
            )
        )

    except Exception as exc:
        try:
            verificacion_error = (
                pago_verificacion_repository
                .crear_verificacion_pago(
                    db,

                    id_solicitud_requisito=(
                        requisito
                        .id_solicitud_requisito
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
                        "tipo":
                            "error_api",

                        "documento_identidad_consultado":
                            documento,
                    },
                )
            )

            registrar_accion_simple(
                db,
                accion=(
                    "verificar_pago_api_error"
                ),
                modulo=(
                    "gestion_seguimiento"
                ),
                id_usuario_actor=(
                    id_usuario_verificador
                ),
                entidad=(
                    "solicitud_requisito"
                ),
                id_entidad=str(
                    requisito
                    .id_solicitud_requisito
                ),
                exitoso=False,
                detalle={
                    "id_solicitud":
                        solicitud.id_solicitud,

                    "resultado":
                        "error",
                },
                direccion_ip=(
                    direccion_ip
                ),
                user_agent=(
                    user_agent
                ),
            )

            # La caída de la API no convierte el requisito
            # en no_cumple.

            requisito.estado_verificacion = (
                "pendiente"
            )

            requisito.fecha_verificacion = (
                None
            )

            requisito.id_usuario_verificador = (
                None
            )

            requisito.detalle_verificacion = (
                None
            )

            # IMPORTANTE:
            # No se registra un evento de historial.
            # El intento queda conservado en verificación
            # de pagos y auditoría.

            db.commit()

            return _crear_resultado(
                verificacion_error,
                mensaje=(
                    "No fue posible verificar el pago "
                    "en este momento. "
                    "Intenta nuevamente más tarde."
                ),
            )

        except Exception:
            db.rollback()

            raise PagoApiNoDisponibleError(
                "No fue posible verificar el pago "
                "en este momento. "
                "Intenta nuevamente más tarde."
            ) from exc

    # ========================================================
    # COMPARACIÓN
    # ========================================================

    verificado, detalle_interno = (
        _evaluar_respuesta_api(
            respuesta=(
                respuesta_api
            ),

            numero_factura_esperado=(
                numero_factura
            ),

            documento_esperado=(
                documento
            ),

            codigo_esperado=(
                codigo_concepto
            ),

            monto_esperado=(
                requisito
                .monto_economico
            ),

            moneda_esperada=(
                requisito.moneda
            ),
        )
    )

    # --------------------------------------------------------
    # Mensaje público.
    #
    # Si la verificación falla no exponemos cuál identificador
    # fue el que produjo la falta de coincidencia.
    # --------------------------------------------------------

    mensaje_publico = (
        "La factura fue verificada correctamente."
        if verificado
        else (
            "No se encontró un pago que coincida "
            "con los datos registrados. "
            "Revisa el CI mostrado y el número de factura."
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

    fecha_verificacion = (
        datetime.now(
            timezone.utc
        )
    )

    detalle_respuesta = (
        respuesta_api.model_dump(
            mode="json"
        )
    )

    detalle_respuesta[
        "documento_identidad_consultado"
    ] = documento

    detalle_respuesta[
        "evaluacion_interna"
    ] = detalle_interno

    # ========================================================
    # REGISTRAR INTENTO
    # ========================================================

    try:
        registro = (
            pago_verificacion_repository
            .crear_verificacion_pago(
                db,

                id_solicitud_requisito=(
                    requisito
                    .id_solicitud_requisito
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

                **_datos_reportados_almacenables(
                    respuesta_api
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
                mensaje_publico
            ),
        )

        registrar_accion_simple(
            db,
            accion=(
                "verificar_pago_solicitud"
            ),
            modulo=(
                "gestion_seguimiento"
            ),
            id_usuario_actor=(
                id_usuario_verificador
            ),
            entidad=(
                "solicitud_requisito"
            ),
            id_entidad=str(
                requisito
                .id_solicitud_requisito
            ),
            exitoso=(
                verificado
            ),
            detalle={
                "id_solicitud":
                    solicitud.id_solicitud,

                "resultado":
                    estado_verificacion_pago,
            },
            direccion_ip=(
                direccion_ip
            ),
            user_agent=(
                user_agent
            ),
        )

        # ====================================================
        # HISTORIAL PÚBLICO
        # ====================================================
        #
        # Solamente una acreditación correcta constituye
        # un hito real del trámite.
        #
        # Los intentos no verificados quedan en:
        #
        # - solicitud_pago_verificacion;
        # - auditoría.
        #
        # ====================================================

        if verificado:
            seguimiento_repo.registrar_historial(
                db,
                solicitud.id_solicitud,
                id_usuario_verificador,
                "pago_verificado",
                (
                    f"Pago verificado: "
                    f"{requisito.nombre}."
                ),
                id_solicitud_etapa=(
                    requisito
                    .id_solicitud_etapa
                ),
                id_solicitud_requisito=(
                    requisito
                    .id_solicitud_requisito
                ),
            )

        db.commit()

        return _crear_resultado(
            registro,
            mensaje=(
                mensaje_publico
            ),
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


# ============================================================
# VERIFICACIÓN ADMINISTRATIVA
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
    seguimiento_repo.bloquear_solicitud(
        db,
        id_solicitud,
    )

    solicitud = (
        solicitud_administrativa_repository
        .obtener_solicitud_administrativa_por_id(
            db,
            id_solicitud,
        )
    )

    if solicitud is None:
        raise SolicitudPagoNoEncontradaError(
            "La solicitud no existe o no está "
            "disponible para gestión administrativa."
        )

    requisito = (
        solicitud_administrativa_repository
        .obtener_requisito_solicitud_por_id(
            db,
            id_solicitud_requisito,
        )
    )

    _validar_requisito_basico(
        solicitud,
        requisito,
        id_solicitud=(
            id_solicitud
        ),
    )

    validar_requisito_editable(
        solicitud,
        requisito,
    )

    return _verificar_pago(
        db,
        solicitud=(
            solicitud
        ),
        requisito=(
            requisito
        ),
        id_usuario_verificador=(
            id_usuario_verificador
        ),
        direccion_ip=(
            direccion_ip
        ),
        user_agent=(
            user_agent
        ),
    )


# ============================================================
# VERIFICACIÓN POR EL SOLICITANTE
# ============================================================


def verificar_pago_solicitante(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitud_requisito: int,
    id_solicitante: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> PagoVerificacionResultadoResponse:
    seguimiento_repo.bloquear_solicitud(
        db,
        id_solicitud,
    )

    solicitud = (
        seguimiento_repo
        .obtener_solicitud_completa(
            db,
            id_solicitud,
        )
    )

    if (
        solicitud is None
        or solicitud.id_solicitante
        != id_solicitante
    ):
        raise SolicitudPagoNoEncontradaError(
            "La solicitud no existe."
        )

    requisito = next(
        (
            item
            for item
            in solicitud.requisitos
            if (
                item.id_solicitud_requisito
                == id_solicitud_requisito
            )
        ),
        None,
    )

    _validar_requisito_basico(
        solicitud,
        requisito,
        id_solicitud=(
            id_solicitud
        ),
    )

    _validar_disponibilidad_solicitante(
        solicitud,
        requisito,
    )

    return _verificar_pago(
        db,
        solicitud=(
            solicitud
        ),
        requisito=(
            requisito
        ),
        id_usuario_verificador=(
            id_solicitante
        ),
        direccion_ip=(
            direccion_ip
        ),
        user_agent=(
            user_agent
        ),
    )