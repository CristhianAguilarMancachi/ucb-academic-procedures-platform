# RETIRO_ENTREGA_FISICA_13F

from __future__ import annotations

from functools import wraps

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import utc_now

from app.models.gestion_seguimiento import (
    SolicitudObservacion,
)

from app.repositories.gestion_seguimiento import (
    seguimiento_repository as repo,
)

from app.schemas.gestion_seguimiento.seguimiento import (
    HistorialPublicoResponse,
    ObservacionCrearRequest,
    ObservacionPublicaResponse,
    ResultadoPublicoResponse,
    SeguimientoResponse,
)

from app.services.auth.audit_service import (
    registrar_accion_simple,
)

from app.services.gestion_seguimiento.datos_pago_service import (
    obtener_documento_pago,
)


# ============================================================
# ERRORES
# ============================================================

class SeguimientoError(Exception):
    def __init__(
        self,
        mensaje: str,
        status_code: int = 409,
    ):
        super().__init__(mensaje)
        self.status_code = status_code


EVENTOS_OPERATIVOS_NO_PUBLICOS = {
    "factura_registrada",
    "pago_no_verificado",
    "pago_verificacion_error",
    "verificar_pago_api_error",
    "etapa_iniciada",
    "etapa_completada",
}


# ============================================================
# TRANSACCIONES
# ============================================================

def transaccion(func):
    """
    Guarda la operación, el historial y la auditoría
    dentro de una misma transacción.
    """

    @wraps(func)
    def ejecutar(
        db: Session,
        *args,
        **kwargs,
    ):
        try:
            resultado = func(
                db,
                *args,
                **kwargs,
            )

            db.commit()
            return resultado

        except IntegrityError as exc:
            db.rollback()

            raise SeguimientoError(
                "La operación entra en conflicto con "
                "un registro existente. Recarga la solicitud."
            ) from exc

        except Exception:
            db.rollback()
            raise

    return ejecutar


# ============================================================
# CONSULTA Y VALIDACIONES
# ============================================================

def obtener_para_accion(
    db: Session,
    id_solicitud: int,
    *,
    id_solicitante: int | None = None,
):
    solicitud = repo.bloquear_solicitud(
        db,
        id_solicitud,
    )

    if (
        solicitud is None
        or (
            id_solicitante is not None
            and solicitud.id_solicitante != id_solicitante
        )
    ):
        raise SeguimientoError(
            "La solicitud no existe.",
            404,
        )

    return repo.obtener_solicitud_completa(
        db,
        id_solicitud,
    )


def exigir_estado(
    solicitud,
    *estados: str,
) -> None:
    if solicitud.estado not in estados:
        raise SeguimientoError(
            "Esta acción no está disponible "
            "en el estado actual de la solicitud."
        )


def requisito_de_solicitud(
    solicitud,
    id_requisito: int,
):
    requisito = next(
        (
            item
            for item in solicitud.requisitos
            if item.id_solicitud_requisito == id_requisito
        ),
        None,
    )

    if requisito is None:
        raise SeguimientoError(
            "El requisito no pertenece a la solicitud.",
            404,
        )

    return requisito


def validar_requisito_editable(
    solicitud,
    requisito,
) -> None:
    """
    Los requisitos se gestionan durante la atención
    administrativa, independientemente de etapas.
    """
    exigir_estado(
        solicitud,
        "en_revision",
        "en_proceso",
    )

    if requisito.id_solicitud != solicitud.id_solicitud:
        raise SeguimientoError(
            "El requisito no pertenece a esta solicitud.",
            404,
        )


def validar_presentacion(
    requisito,
) -> None:
    if (
        requisito.requiere_presentacion_fisica
        and not requisito.presentado
    ):
        raise SeguimientoError(
            "Registra primero la presentación "
            "física del requisito."
        )


def exigir_sin_observaciones(
    db: Session,
    id_solicitud: int,
) -> None:
    observaciones = repo.listar_observaciones(
        db,
        id_solicitud,
    )

    if any(
        item.estado == "pendiente"
        for item in observaciones
    ):
        raise SeguimientoError(
            "La solicitud tiene observaciones pendientes."
        )


def exigir_requisitos(
    requisitos,
) -> None:
    """
    Todos los requisitos obligatorios deben cumplirse.

    - Físicos: recepción y cumplimiento simultáneos.
    - Administrativos: confirmación institucional.
    - Económicos: verificación mediante API.
    """

    faltantes = [
        requisito.nombre
        for requisito in requisitos
        if (
            requisito.obligatorio
            and (
                requisito.estado_verificacion != "cumple"
                or (
                    requisito.requiere_presentacion_fisica
                    and not requisito.presentado
                )
            )
        )
    ]

    if faltantes:
        raise SeguimientoError(
            "Faltan requisitos obligatorios: "
            + ", ".join(faltantes)
            + "."
        )


# ============================================================
# HISTORIAL Y AUDITORÍA
# ============================================================

def evento(
    db: Session,
    solicitud,
    actor: int,
    codigo: str,
    detalle: str,
    *,
    visible: bool = True,
    requisito: int | None = None,
) -> None:
    repo.registrar_historial(
        db,
        solicitud.id_solicitud,
        actor,
        codigo,
        detalle,
        visible_solicitante=visible,
        id_solicitud_requisito=requisito,
    )

    registrar_accion_simple(
        db,
        accion=codigo,
        modulo="gestion_seguimiento",
        id_usuario_actor=actor,
        entidad="solicitud",
        id_entidad=solicitud.id_solicitud,
        detalle={
            "descripcion": detalle,
            "estado": solicitud.estado,
        },
    )


# ============================================================
# SEGUIMIENTO DEL SOLICITANTE
# ============================================================

def consultar_seguimiento(
    db: Session,
    id_solicitud: int,
    id_solicitante: int,
) -> SeguimientoResponse:
    solicitud = repo.obtener_solicitud_completa(
        db,
        id_solicitud,
    )

    if (
        solicitud is None
        or solicitud.id_solicitante != id_solicitante
    ):
        raise SeguimientoError(
            "La solicitud no existe.",
            404,
        )

    observaciones = repo.listar_observaciones(
        db,
        id_solicitud,
    )

    resultado = repo.obtener_resultado(
        db,
        id_solicitud,
    )

    historial_publico = [
        item
        for item in repo.listar_historial(
            db,
            id_solicitud,
            solo_visible=True,
        )
        if (
            item.evento
            not in EVENTOS_OPERATIVOS_NO_PUBLICOS
        )
    ]

    avance = (
        100
        if solicitud.estado in {
            "lista_para_entrega",
            "finalizada",
        }
        else 0
    )

    return SeguimientoResponse(
        id_solicitud=id_solicitud,
        identificador=f"Solicitud #{id_solicitud}",
        nombre_tramite=(
            solicitud.nombre_tramite_snapshot
            or solicitud.tramite.nombre
        ),
        estado=solicitud.estado,
        tipo_intervencion=(
            solicitud.tipo_intervencion
        ),
        avance_porcentaje=avance,
        observaciones=[
            ObservacionPublicaResponse.model_validate(
                item
            )
            for item in observaciones
        ],
        observaciones_pendientes=sum(
            item.estado == "pendiente"
            for item in observaciones
        ),
        historial=[
            HistorialPublicoResponse.model_validate(
                item
            )
            for item in historial_publico
        ],
        resultado=(
            ResultadoPublicoResponse.model_validate(
                resultado
            )
            if resultado is not None
            else None
        ),
    )


# ============================================================
# CANCELACIÓN DEL SOLICITANTE
# ============================================================

@transaccion
def cancelar(
    db: Session,
    id_solicitud: int,
    actor: int,
    motivo: str,
) -> None:
    solicitud = obtener_para_accion(
        db,
        id_solicitud,
        id_solicitante=actor,
    )

    exigir_estado(
        solicitud,
        "borrador",
        "pendiente_recepcion",
    )

    tiene_factura = any(
        requisito.numero_factura
        for requisito in solicitud.requisitos
    )

    tiene_pago_verificado = any(
        pago.estado == "verificado"
        for pago in repo.listar_pagos(
            db,
            id_solicitud,
        )
    )

    if tiene_factura or tiene_pago_verificado:
        raise SeguimientoError(
            "No se permite cancelación automática "
            "con factura registrada. "
            "No se gestionan reembolsos."
        )

    solicitud.estado = "cancelada"
    solicitud.fecha_actualizacion = utc_now()

    evento(
        db,
        solicitud,
        actor,
        "solicitud_cancelada",
        motivo,
    )


# ============================================================
# REGISTRO DE FACTURA
# ============================================================

@transaccion
def registrar_factura(
    db: Session,
    id_solicitud: int,
    id_requisito: int,
    actor: int,
    numero_factura: str,
) -> None:
    solicitud = obtener_para_accion(
        db,
        id_solicitud,
        id_solicitante=actor,
    )

    exigir_estado(
        solicitud,
        "pendiente_recepcion",
        "en_revision",
        "en_proceso",
    )

    requisito = requisito_de_solicitud(
        solicitud,
        id_requisito,
    )

    if not requisito.es_economico:
        raise SeguimientoError(
            "El requisito no es económico.",
            400,
        )

    acreditado = (
        requisito.estado_verificacion == "cumple"
        or any(
            pago.estado == "verificado"
            and pago.id_solicitud_requisito == id_requisito
            for pago in repo.listar_pagos(
                db,
                id_solicitud,
            )
        )
    )

    if acreditado:
        if requisito.numero_factura == numero_factura:
            return

        raise SeguimientoError(
            "Una factura acreditada no puede sustituirse."
        )

    if any(
        otro.id_solicitud_requisito != id_requisito
        and otro.numero_factura == numero_factura
        for otro in solicitud.requisitos
    ):
        raise SeguimientoError(
            "Esta factura ya está registrada "
            "en otro requisito de la solicitud."
        )

    if not obtener_documento_pago(
        db,
        solicitud,
    ):
        raise SeguimientoError(
            "Registra tu documento de identidad "
            "antes de registrar una factura.",
            400,
        )

    if requisito.numero_factura == numero_factura:
        return

    requisito.numero_factura = numero_factura
    requisito.estado_verificacion = "pendiente"
    requisito.id_usuario_verificador = None
    requisito.fecha_verificacion = None
    requisito.detalle_verificacion = None

    registrar_accion_simple(
        db,
        accion="registrar_factura_pago",
        modulo="gestion_seguimiento",
        id_usuario_actor=actor,
        entidad="solicitud_requisito",
        id_entidad=requisito.id_solicitud_requisito,
        exitoso=True,
        detalle={
            "id_solicitud": id_solicitud,
            "estado": "pendiente_verificacion",
        },
    )


# ============================================================
# DECLARACIÓN FÍSICA DEL SOLICITANTE
# ============================================================

@transaccion
def declarar_entrega_fisica(
    db: Session,
    id_solicitud: int,
    id_requisito: int,
    actor: int,
) -> None:
    solicitud = obtener_para_accion(
        db,
        id_solicitud,
        id_solicitante=actor,
    )

    exigir_estado(
        solicitud,
        "pendiente_recepcion",
        "en_revision",
        "en_proceso",
    )

    requisito = requisito_de_solicitud(
        solicitud,
        id_requisito,
    )

    if not requisito.requiere_presentacion_fisica:
        raise SeguimientoError(
            "El requisito no requiere "
            "presentación física.",
            400,
        )

    if requisito.presentado:
        return

    declaracion_existente = any(
        item.evento == "entrega_fisica_declarada"
        and item.id_solicitud_requisito == id_requisito
        for item in repo.listar_historial(
            db,
            id_solicitud,
        )
    )

    if declaracion_existente:
        return

    evento(
        db,
        solicitud,
        actor,
        "entrega_fisica_declarada",
        (
            "El solicitante declara haber entregado "
            f"físicamente: {requisito.nombre}. "
            "Pendiente de recepción administrativa."
        ),
        requisito=id_requisito,
    )


# ============================================================
# RECEPCIÓN FÍSICA ADMINISTRATIVA
# ============================================================

@transaccion
def registrar_presentacion(
    db: Session,
    id_solicitud: int,
    id_requisito: int,
    actor: int,
) -> None:
    """
    Registra la recepción física y el cumplimiento
    del documento en una misma operación.

    No requiere una segunda verificación individual.

    Si el documento ya fue recibido, la operación
    es idempotente y no genera eventos duplicados.
    """

    solicitud = obtener_para_accion(
        db,
        id_solicitud,
    )

    requisito = requisito_de_solicitud(
        solicitud,
        id_requisito,
    )

    validar_requisito_editable(
        solicitud,
        requisito,
    )

    if not requisito.requiere_presentacion_fisica:
        raise SeguimientoError(
            "El requisito no requiere "
            "presentación física.",
            400,
        )

    if requisito.es_economico:
        raise SeguimientoError(
            "Un requisito económico debe verificarse "
            "mediante la API de pagos.",
            400,
        )

    if requisito.presentado:
        if requisito.estado_verificacion != "cumple":
            raise SeguimientoError(
                "El documento ya fue recibido, pero "
                "su estado anterior requiere regularización."
            )

        return

    fecha = utc_now()

    # Una sola operación registra recepción y cumplimiento.
    requisito.presentado = True
    requisito.fecha_presentacion = fecha
    requisito.id_usuario_presentacion = actor

    requisito.estado_verificacion = "cumple"
    requisito.id_usuario_verificador = actor
    requisito.fecha_verificacion = fecha

    requisito.detalle_verificacion = (
        "Cumplimiento registrado junto con la "
        "recepción física del documento."
    )

    requisito.fecha_actualizacion = fecha

    solicitud.fecha_actualizacion = fecha

    evento(
        db,
        solicitud,
        actor,
        "requisito_fisico_recibido",
        (
            "Documento físico recibido y requisito "
            f"cumplido: {requisito.nombre}."
        ),
        requisito=requisito.id_solicitud_requisito,
    )


# ============================================================
# OBSERVACIONES
# ============================================================

@transaccion
def crear_observacion(
    db: Session,
    id_solicitud: int,
    actor: int,
    datos: ObservacionCrearRequest,
) -> None:
    solicitud = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        solicitud,
        "en_revision",
        "en_proceso",
    )

    if datos.id_solicitud_requisito is not None:
        requisito = requisito_de_solicitud(
            solicitud,
            datos.id_solicitud_requisito,
        )

        validar_requisito_editable(
            solicitud,
            requisito,
        )

    observacion = SolicitudObservacion(
        id_solicitud=id_solicitud,
        id_usuario_observador=actor,
        estado="pendiente",
        **datos.model_dump(),
    )

    db.add(observacion)

    evento(
        db,
        solicitud,
        actor,
        "observacion_registrada",
        datos.detalle,
        requisito=datos.id_solicitud_requisito,
    )


@transaccion
def resolver_observacion(
    db: Session,
    id_solicitud: int,
    id_observacion: int,
    actor: int,
) -> None:
    solicitud = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        solicitud,
        "en_revision",
        "en_proceso",
    )

    observacion = next(
        (
            item
            for item in repo.listar_observaciones(
                db,
                id_solicitud,
            )
            if item.id_observacion == id_observacion
        ),
        None,
    )

    if observacion is None:
        raise SeguimientoError(
            "La observación no pertenece a la solicitud.",
            404,
        )

    if observacion.estado == "resuelta":
        return

    observacion.estado = "resuelta"
    observacion.id_usuario_resolucion = actor
    observacion.fecha_resolucion = utc_now()

    evento(
        db,
        solicitud,
        actor,
        "observacion_resuelta",
        f"Observación resuelta: {observacion.detalle}",
        requisito=observacion.id_solicitud_requisito,
    )


# ============================================================
# RECHAZO ADMINISTRATIVO
# ============================================================

@transaccion
def rechazar(
    db: Session,
    id_solicitud: int,
    actor: int,
    motivo: str,
) -> None:
    solicitud = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        solicitud,
        "pendiente_recepcion",
        "en_revision",
        "en_proceso",
    )

    solicitud.estado = "rechazada"
    solicitud.fecha_actualizacion = utc_now()

    evento(
        db,
        solicitud,
        actor,
        "solicitud_rechazada",
        motivo,
    )


# ============================================================
# ENTREGA FINAL
# ============================================================

