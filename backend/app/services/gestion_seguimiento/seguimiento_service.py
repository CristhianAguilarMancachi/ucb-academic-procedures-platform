from __future__ import annotations

from functools import wraps

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models.gestion_seguimiento import (
    SolicitudEntrega,
    SolicitudObservacion,
    SolicitudResultado,
)
from app.repositories.gestion_seguimiento import (
    seguimiento_repository as repo,
)
from app.schemas.gestion_seguimiento.seguimiento import (
    EntregaRegistrarRequest,
    HistorialPublicoResponse,
    ObservacionCrearRequest,
    ObservacionPublicaResponse,
    ResultadoPublicoResponse,
    ResultadoRegistrarRequest,
    SeguimientoResponse,
    SolicitudEtapaPublicaResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)
from app.services.gestion_seguimiento.datos_pago_service import (
    obtener_documento_pago,
)


class SeguimientoError(Exception):
    def __init__(
        self,
        mensaje: str,
        status_code: int = 409,
    ):
        super().__init__(
            mensaje
        )

        self.status_code = (
            status_code
        )


# ============================================================
# EVENTOS QUE NO SON HITOS DEL TIMELINE DEL SOLICITANTE
# ============================================================
#
# Estos eventos pueden haber sido generados por versiones
# anteriores del sistema, pero no representan un avance real
# del trámite.
#
# - registrar/cambiar una factura es una acción operativa;
# - un intento de pago fallido no constituye un nuevo estado;
# - un error técnico de la API tampoco constituye un hito.
#
# Los intentos de pago quedan registrados en la tabla
# solicitud_pago_verificacion y en auditoría.
# ============================================================


EVENTOS_OPERATIVOS_NO_PUBLICOS = {
    "factura_registrada",
    "pago_no_verificado",
    "pago_verificacion_error",
    "verificar_pago_api_error",
}


def transaccion(
    func,
):
    """
    Las acciones confirman estado, historial y auditoría
    dentro de la misma transacción.
    """

    @wraps(
        func
    )
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
                "La operación entra en conflicto con un "
                "registro existente. Recarga la solicitud."
            ) from exc

        except Exception:
            db.rollback()
            raise

    return ejecutar


def obtener_para_accion(
    db,
    id_solicitud,
    *,
    id_solicitante=None,
):
    solicitud = (
        repo.bloquear_solicitud(
            db,
            id_solicitud,
        )
    )

    if (
        solicitud is None
        or (
            id_solicitante
            is not None
            and solicitud.id_solicitante
            != id_solicitante
        )
    ):
        raise SeguimientoError(
            "La solicitud no existe.",
            404,
        )

    return (
        repo.obtener_solicitud_completa(
            db,
            id_solicitud,
        )
    )


def exigir_estado(
    solicitud,
    *estados,
):
    if (
        solicitud.estado
        not in estados
    ):
        raise SeguimientoError(
            "Esta acción no está disponible "
            "en el estado actual de la solicitud."
        )


def requisito_de_solicitud(
    solicitud,
    id_requisito,
):
    requisito = next(
        (
            requisito
            for requisito
            in solicitud.requisitos
            if (
                requisito.id_solicitud_requisito
                == id_requisito
            )
        ),
        None,
    )

    if requisito is None:
        raise SeguimientoError(
            "El requisito no pertenece "
            "a la solicitud.",
            404,
        )

    return requisito


def validar_requisito_editable(
    solicitud,
    requisito,
):
    exigir_estado(
        solicitud,
        "en_revision",
        "en_proceso",
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
        raise SeguimientoError(
            "El requisito solo puede gestionarse "
            "durante su etapa."
        )


def validar_presentacion(
    requisito,
):
    if (
        requisito.requiere_presentacion_fisica
        and not requisito.presentado
    ):
        raise SeguimientoError(
            "Registra primero la presentación "
            "física del requisito."
        )


def exigir_sin_observaciones(
    db,
    id_solicitud,
):
    if any(
        observacion.estado
        == "pendiente"
        for observacion
        in repo.listar_observaciones(
            db,
            id_solicitud,
        )
    ):
        raise SeguimientoError(
            "La solicitud tiene observaciones pendientes."
        )


def exigir_requisitos(
    requisitos,
):
    faltantes = [
        requisito.nombre
        for requisito
        in requisitos
        if (
            requisito.obligatorio
            and (
                requisito.estado_verificacion
                != "cumple"
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
            + ", ".join(
                faltantes
            )
            + "."
        )


def evento(
    db,
    solicitud,
    actor,
    codigo,
    detalle,
    *,
    visible=True,
    etapa=None,
    requisito=None,
):
    repo.registrar_historial(
        db,
        solicitud.id_solicitud,
        actor,
        codigo,
        detalle,
        visible_solicitante=visible,
        id_solicitud_etapa=etapa,
        id_solicitud_requisito=requisito,
    )

    registrar_accion_simple(
        db,
        accion=codigo,
        modulo="gestion_seguimiento",
        id_usuario_actor=actor,
        entidad="solicitud",
        id_entidad=(
            solicitud.id_solicitud
        ),
        detalle={
            "descripcion":
                detalle,

            "estado":
                solicitud.estado,
        },
    )


# ============================================================
# CONSULTA DE SEGUIMIENTO
# ============================================================


def consultar_seguimiento(
    db,
    id_solicitud,
    id_solicitante,
):
    s = (
        repo.obtener_solicitud_completa(
            db,
            id_solicitud,
        )
    )

    if (
        s is None
        or s.id_solicitante
        != id_solicitante
    ):
        raise SeguimientoError(
            "La solicitud no existe.",
            404,
        )

    etapas = (
        repo.listar_etapas(
            db,
            id_solicitud,
        )
    )

    publicas = [
        etapa
        for etapa
        in etapas
        if etapa.visible_solicitante
    ]

    actual = next(
        (
            etapa
            for etapa
            in publicas
            if (
                etapa.id_solicitud_etapa
                == s.id_etapa_actual
            )
        ),
        None,
    )

    obs = (
        repo.listar_observaciones(
            db,
            id_solicitud,
        )
    )

    resultado = (
        repo.obtener_resultado(
            db,
            id_solicitud,
        )
    )

    entrega = (
        repo.obtener_entrega(
            db,
            id_solicitud,
        )
    )

    avance = (
        round(
            100
            * sum(
                etapa.estado
                == "completada"
                for etapa
                in etapas
            )
            / len(
                etapas
            )
        )
        if etapas
        else 0
    )

    if (
        s.estado
        in (
            "lista_para_entrega",
            "finalizada",
        )
    ):
        avance = 100

    # --------------------------------------------------------
    # HISTORIAL PÚBLICO
    # --------------------------------------------------------
    #
    # También filtramos eventos antiguos ya almacenados.
    # De esta forma no es necesario eliminar información
    # histórica de la base de datos para limpiar el timeline.
    # --------------------------------------------------------

    historial_publico = [
        historial
        for historial
        in repo.listar_historial(
            db,
            id_solicitud,
            solo_visible=True,
        )
        if (
            historial.evento
            not in EVENTOS_OPERATIVOS_NO_PUBLICOS
        )
    ]

    return SeguimientoResponse(
        id_solicitud=id_solicitud,

        identificador=(
            f"Solicitud #{id_solicitud}"
        ),

        nombre_tramite=(
            s.nombre_tramite_snapshot
            or s.tramite.nombre
        ),

        estado=s.estado,

        etapa_actual=(
            SolicitudEtapaPublicaResponse
            .model_validate(
                actual
            )
            if actual
            else None
        ),

        etapas=[
            SolicitudEtapaPublicaResponse
            .model_validate(
                etapa
            )
            for etapa
            in publicas
        ],

        avance_porcentaje=(
            avance
        ),

        observaciones=[
            ObservacionPublicaResponse
            .model_validate(
                observacion
            )
            for observacion
            in obs
        ],

        observaciones_pendientes=sum(
            observacion.estado
            == "pendiente"
            for observacion
            in obs
        ),

        historial=[
            HistorialPublicoResponse
            .model_validate(
                historial
            )
            for historial
            in historial_publico
        ],

        resultado=(
            ResultadoPublicoResponse
            .model_validate(
                resultado
            )
            if resultado
            else None
        ),

        fecha_entrega=(
            entrega.fecha_entrega
            if entrega
            else None
        ),
    )


# ============================================================
# CANCELAR
# ============================================================


@transaccion
def cancelar(
    db,
    id_solicitud,
    actor,
    motivo,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
        id_solicitante=actor,
    )

    exigir_estado(
        s,
        "borrador",
        "pendiente_recepcion",
    )

    if (
        any(
            requisito.numero_factura
            for requisito
            in s.requisitos
        )
        or any(
            pago.estado
            == "verificado"
            for pago
            in repo.listar_pagos(
                db,
                id_solicitud,
            )
        )
    ):
        raise SeguimientoError(
            "No se permite cancelación automática "
            "con factura registrada. "
            "No se gestionan reembolsos."
        )

    s.estado = "cancelada"

    evento(
        db,
        s,
        actor,
        "solicitud_cancelada",
        motivo,
    )


# ============================================================
# FACTURA
# ============================================================


@transaccion
def registrar_factura(
    db,
    id_solicitud,
    id_requisito,
    actor,
    numero_factura,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
        id_solicitante=actor,
    )

    exigir_estado(
        s,
        "pendiente_recepcion",
        "en_revision",
        "en_proceso",
    )

    r = requisito_de_solicitud(
        s,
        id_requisito,
    )

    if not r.es_economico:
        raise SeguimientoError(
            "El requisito no es económico.",
            400,
        )

    if (
        r.id_solicitud_etapa
        is not None
        and (
            s.estado
            != "en_proceso"
            or r.id_solicitud_etapa
            != s.id_etapa_actual
        )
    ):
        raise SeguimientoError(
            "Registra la factura cuando la "
            "solicitud llegue a la etapa correspondiente."
        )

    if (
        r.estado_verificacion
        == "cumple"
        or any(
            pago.estado
            == "verificado"
            and pago.id_solicitud_requisito
            == id_requisito
            for pago
            in repo.listar_pagos(
                db,
                id_solicitud,
            )
        )
    ):
        if (
            r.numero_factura
            == numero_factura
        ):
            return

        raise SeguimientoError(
            "Una factura acreditada no puede sustituirse."
        )

    if any(
        requisito.id_solicitud_requisito
        != id_requisito
        and requisito.numero_factura
        == numero_factura
        for requisito
        in s.requisitos
    ):
        raise SeguimientoError(
            "Esta factura ya está registrada "
            "en otro requisito de la solicitud."
        )

    if not obtener_documento_pago(
        db,
        s,
    ):
        raise SeguimientoError(
            "Registra tu documento de identidad "
            "antes de registrar una factura.",
            400,
        )

    if (
        r.numero_factura
        == numero_factura
    ):
        return

    r.numero_factura = (
        numero_factura
    )

    r.estado_verificacion = (
        "pendiente"
    )

    r.id_usuario_verificador = (
        None
    )

    r.fecha_verificacion = (
        None
    )

    r.detalle_verificacion = (
        None
    )

    # --------------------------------------------------------
    # La factura NO es un hito del timeline.
    #
    # Conservamos la acción únicamente en auditoría.
    # --------------------------------------------------------

    registrar_accion_simple(
        db,
        accion="registrar_factura_pago",
        modulo="gestion_seguimiento",
        id_usuario_actor=actor,
        entidad="solicitud_requisito",
        id_entidad=(
            r.id_solicitud_requisito
        ),
        exitoso=True,
        detalle={
            "id_solicitud":
                s.id_solicitud,

            "estado":
                "pendiente_verificacion",
        },
    )


# ============================================================
# DECLARACIÓN FÍSICA DEL SOLICITANTE
# ============================================================


@transaccion
def declarar_entrega_fisica(
    db,
    id_solicitud,
    id_requisito,
    actor,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
        id_solicitante=actor,
    )

    exigir_estado(
        s,
        "pendiente_recepcion",
        "en_revision",
        "en_proceso",
    )

    r = requisito_de_solicitud(
        s,
        id_requisito,
    )

    if (
        not r.requiere_presentacion_fisica
    ):
        raise SeguimientoError(
            "El requisito no requiere "
            "presentación física.",
            400,
        )

    if (
        r.id_solicitud_etapa
        is not None
        and (
            s.estado
            != "en_proceso"
            or r.id_solicitud_etapa
            != s.id_etapa_actual
        )
    ):
        raise SeguimientoError(
            "Confirma la entrega cuando la "
            "solicitud llegue a la etapa correspondiente."
        )

    if (
        r.presentado
        or any(
            historial.evento
            == "entrega_fisica_declarada"
            and historial.id_solicitud_requisito
            == id_requisito
            for historial
            in repo.listar_historial(
                db,
                id_solicitud,
            )
        )
    ):
        return

    evento(
        db,
        s,
        actor,
        "entrega_fisica_declarada",
        (
            "El solicitante declara haber entregado "
            f"físicamente: {r.nombre}. "
            "Pendiente de recepción y verificación "
            "administrativa."
        ),
        etapa=(
            r.id_solicitud_etapa
        ),
        requisito=(
            id_requisito
        ),
    )


# ============================================================
# RECEPCIÓN FÍSICA ADMINISTRATIVA
# ============================================================


@transaccion
def registrar_presentacion(
    db,
    id_solicitud,
    id_requisito,
    actor,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
    )

    r = requisito_de_solicitud(
        s,
        id_requisito,
    )

    validar_requisito_editable(
        s,
        r,
    )

    if (
        not r.requiere_presentacion_fisica
    ):
        raise SeguimientoError(
            "El requisito no requiere "
            "presentación física.",
            400,
        )

    r.presentado = True

    r.fecha_presentacion = (
        utc_now()
    )

    r.id_usuario_presentacion = (
        actor
    )

    # La recepción física no cambia automáticamente
    # el juicio administrativo del requisito.

    evento(
        db,
        s,
        actor,
        "requisito_fisico_recibido",
        (
            "Presentación física registrada: "
            f"{r.nombre}."
        ),
        etapa=(
            r.id_solicitud_etapa
        ),
        requisito=(
            r.id_solicitud_requisito
        ),
    )


# ============================================================
# ETAPAS
# ============================================================


def iniciar_etapa(
    db,
    s,
    etapa,
    actor,
):
    etapa.estado = (
        "en_curso"
    )

    etapa.id_usuario_inicio = (
        actor
    )

    etapa.fecha_inicio = (
        utc_now()
    )

    s.id_etapa_actual = (
        etapa.id_solicitud_etapa
    )

    evento(
        db,
        s,
        actor,
        "etapa_iniciada",
        (
            "Etapa iniciada: "
            f"{etapa.nombre}."
        ),
        visible=(
            etapa.visible_solicitante
        ),
        etapa=(
            etapa.id_solicitud_etapa
        ),
    )


@transaccion
def iniciar_procesamiento(
    db,
    id_solicitud,
    actor,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        s,
        "en_revision",
    )

    exigir_sin_observaciones(
        db,
        id_solicitud,
    )

    exigir_requisitos(
        [
            requisito
            for requisito
            in s.requisitos
            if (
                requisito.id_solicitud_etapa
                is None
            )
        ]
    )

    etapas = (
        repo.listar_etapas(
            db,
            id_solicitud,
        )
    )

    if any(
        etapa.estado
        != "pendiente"
        for etapa
        in etapas
    ):
        raise SeguimientoError(
            "El estado de las etapas es "
            "incompatible con el inicio."
        )

    if not etapas:
        raise SeguimientoError(
            "Solicitud anterior sin etapas: "
            "registra el resultado desde revisión; "
            "no se crean etapas históricas."
        )

    s.estado = (
        "en_proceso"
    )

    s.id_etapa_actual = (
        etapas[
            0
        ].id_solicitud_etapa
    )

    evento(
        db,
        s,
        actor,
        "procesamiento_iniciado",
        "Procesamiento iniciado.",
        etapa=(
            s.id_etapa_actual
        ),
    )

    iniciar_etapa(
        db,
        s,
        etapas[0],
        actor,
    )


@transaccion
def avanzar_etapa(
    db,
    id_solicitud,
    actor,
    id_etapa_esperada,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        s,
        "en_proceso",
    )

    exigir_sin_observaciones(
        db,
        id_solicitud,
    )

    if (
        s.id_etapa_actual
        != id_etapa_esperada
    ):
        raise SeguimientoError(
            "La etapa cambió. Recarga la solicitud "
            "antes de continuar."
        )

    etapas = (
        repo.listar_etapas(
            db,
            id_solicitud,
        )
    )

    actual = next(
        (
            etapa
            for etapa
            in etapas
            if (
                etapa.id_solicitud_etapa
                == s.id_etapa_actual
            )
        ),
        None,
    )

    if (
        actual is None
        or actual.estado
        != "en_curso"
    ):
        raise SeguimientoError(
            "No existe una etapa en curso."
        )

    exigir_requisitos(
        [
            requisito
            for requisito
            in s.requisitos
            if (
                requisito.id_solicitud_etapa
                in (
                    None,
                    actual.id_solicitud_etapa,
                )
            )
        ]
    )

    actual.estado = (
        "completada"
    )

    actual.fecha_finalizacion = (
        utc_now()
    )

    actual.id_usuario_finalizacion = (
        actor
    )

    db.flush()

    evento(
        db,
        s,
        actor,
        "etapa_completada",
        (
            "Etapa completada: "
            f"{actual.nombre}."
        ),
        visible=(
            actual.visible_solicitante
        ),
        etapa=(
            actual.id_solicitud_etapa
        ),
    )

    siguiente = next(
        (
            etapa
            for etapa
            in etapas
            if (
                etapa.orden
                > actual.orden
            )
        ),
        None,
    )

    if siguiente:
        if (
            siguiente.estado
            != "pendiente"
        ):
            raise SeguimientoError(
                "La siguiente etapa no está pendiente."
            )

        iniciar_etapa(
            db,
            s,
            siguiente,
            actor,
        )


# ============================================================
# OBSERVACIONES
# ============================================================


@transaccion
def crear_observacion(
    db,
    id_solicitud,
    actor,
    datos: ObservacionCrearRequest,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        s,
        "en_revision",
        "en_proceso",
    )

    if (
        datos.id_solicitud_etapa
        is not None
        and datos.id_solicitud_etapa
        != s.id_etapa_actual
    ):
        raise SeguimientoError(
            "La observación debe corresponder "
            "a la etapa actual."
        )

    if (
        datos.id_solicitud_requisito
        is not None
    ):
        r = requisito_de_solicitud(
            s,
            datos.id_solicitud_requisito,
        )

        validar_requisito_editable(
            s,
            r,
        )

        if (
            datos.id_solicitud_etapa
            is not None
            and r.id_solicitud_etapa
            != datos.id_solicitud_etapa
        ):
            raise SeguimientoError(
                "La etapa y el requisito indicados "
                "no coinciden.",
                400,
            )

    obs = SolicitudObservacion(
        id_solicitud=(
            id_solicitud
        ),

        id_usuario_observador=(
            actor
        ),

        estado="pendiente",

        **datos.model_dump(),
    )

    db.add(
        obs
    )

    evento(
        db,
        s,
        actor,
        "observacion_registrada",
        datos.detalle,
        etapa=(
            datos.id_solicitud_etapa
        ),
        requisito=(
            datos.id_solicitud_requisito
        ),
    )


@transaccion
def resolver_observacion(
    db,
    id_solicitud,
    id_observacion,
    actor,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        s,
        "en_revision",
        "en_proceso",
    )

    obs = next(
        (
            observacion
            for observacion
            in repo.listar_observaciones(
                db,
                id_solicitud,
            )
            if (
                observacion.id_observacion
                == id_observacion
            )
        ),
        None,
    )

    if obs is None:
        raise SeguimientoError(
            "La observación no pertenece "
            "a la solicitud.",
            404,
        )

    if (
        obs.estado
        == "resuelta"
    ):
        return

    obs.estado = (
        "resuelta"
    )

    obs.id_usuario_resolucion = (
        actor
    )

    obs.fecha_resolucion = (
        utc_now()
    )

    evento(
        db,
        s,
        actor,
        "observacion_resuelta",
        (
            "Observación resuelta: "
            f"{obs.detalle}"
        ),
        etapa=(
            obs.id_solicitud_etapa
        ),
        requisito=(
            obs.id_solicitud_requisito
        ),
    )


# ============================================================
# RECHAZO
# ============================================================


@transaccion
def rechazar(
    db,
    id_solicitud,
    actor,
    motivo,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        s,
        "pendiente_recepcion",
        "en_revision",
        "en_proceso",
    )

    s.estado = (
        "rechazada"
    )

    evento(
        db,
        s,
        actor,
        "solicitud_rechazada",
        motivo,
        etapa=(
            s.id_etapa_actual
        ),
    )


# ============================================================
# RESULTADO
# ============================================================


@transaccion
def registrar_resultado(
    db,
    id_solicitud,
    actor,
    datos: ResultadoRegistrarRequest,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        s,
        "en_revision",
        "en_proceso",
    )

    etapas = (
        repo.listar_etapas(
            db,
            id_solicitud,
        )
    )

    if (
        s.estado
        == "en_revision"
        and etapas
    ):
        raise SeguimientoError(
            "Debes iniciar y completar las etapas "
            "antes de registrar el resultado."
        )

    exigir_sin_observaciones(
        db,
        id_solicitud,
    )

    exigir_requisitos(
        s.requisitos
    )

    if any(
        etapa.estado
        != "completada"
        for etapa
        in etapas
    ):
        raise SeguimientoError(
            "Todavía quedan etapas por completar."
        )

    if (
        repo.obtener_resultado(
            db,
            id_solicitud,
        )
    ):
        raise SeguimientoError(
            "La solicitud ya tiene un resultado."
        )

    tipo = (
        s.tipo_finalizacion
        or datos.tipo_finalizacion
    )

    if tipo is None:
        raise SeguimientoError(
            "Solicitud anterior sin modalidad capturada: "
            "indica el tipo de finalización.",
            400,
        )

    if (
        s.tipo_finalizacion
        and datos.tipo_finalizacion
        and s.tipo_finalizacion
        != datos.tipo_finalizacion
    ):
        raise SeguimientoError(
            "No se puede cambiar la modalidad "
            "capturada al enviar.",
            400,
        )

    s.tipo_finalizacion = (
        tipo
    )

    db.add(
        SolicitudResultado(
            id_solicitud=(
                id_solicitud
            ),

            tipo_finalizacion=(
                tipo
            ),

            detalle=(
                datos.detalle
            ),

            id_usuario_registro=(
                actor
            ),
        )
    )

    evento(
        db,
        s,
        actor,
        "resultado_registrado",
        (
            datos.detalle
            or "Resultado registrado."
        ),
        etapa=(
            s.id_etapa_actual
        ),
    )

    s.estado = (
        "lista_para_entrega"
        if tipo == "entrega"
        else "finalizada"
    )

    s.id_etapa_actual = (
        None
    )

    evento(
        db,
        s,
        actor,
        (
            "lista_para_entrega"
            if tipo == "entrega"
            else "solicitud_finalizada"
        ),
        (
            "Disponible para recojo."
            if tipo == "entrega"
            else "Solicitud finalizada."
        ),
    )


# ============================================================
# ENTREGA FINAL
# ============================================================


@transaccion
def registrar_entrega(
    db,
    id_solicitud,
    actor,
    datos: EntregaRegistrarRequest,
):
    s = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        s,
        "lista_para_entrega",
    )

    exigir_sin_observaciones(
        db,
        id_solicitud,
    )

    exigir_requisitos(
        s.requisitos
    )

    resultado = (
        repo.obtener_resultado(
            db,
            id_solicitud,
        )
    )

    if (
        s.tipo_finalizacion
        != "entrega"
        or resultado is None
        or resultado.tipo_finalizacion
        != "entrega"
    ):
        raise SeguimientoError(
            "La solicitud no tiene un resultado "
            "para entrega."
        )

    if (
        repo.obtener_entrega(
            db,
            id_solicitud,
        )
    ):
        raise SeguimientoError(
            "La entrega ya fue registrada."
        )

    db.add(
        SolicitudEntrega(
            id_solicitud=(
                id_solicitud
            ),

            id_usuario_entrega=(
                actor
            ),

            **datos.model_dump(),
        )
    )

    s.estado = (
        "finalizada"
    )

    evento(
        db,
        s,
        actor,
        "entrega_registrada",
        "Entrega/recojo registrado.",
    )

    evento(
        db,
        s,
        actor,
        "solicitud_finalizada",
        "Solicitud finalizada.",
    )