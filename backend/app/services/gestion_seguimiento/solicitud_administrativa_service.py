from __future__ import annotations

from datetime import (
    date,
    datetime,
    timezone,
)

from sqlalchemy.exc import (
    IntegrityError,
)
from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento import (
    seguimiento_repository
    as seguimiento_repo,
)
from app.repositories.gestion_seguimiento import (
    solicitud_administrativa_repository,
)
from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoVerificacionResponse,
)
from app.schemas.gestion_seguimiento.seguimiento import (
    EntregaResponse,
    HistorialResponse,
    ObservacionResponse,
    ResultadoResponse,
    SolicitudEtapaResponse,
)
from app.schemas.gestion_seguimiento.solicitud_administrativa import (
    ListaSolicitudesAdministrativasResponse,
    RequisitoVerificacionResponse,
    RequisitoVerificarRequest,
    SolicitudAdministrativaDetalleResponse,
    SolicitudAdministrativaResumenResponse,
    SolicitudDatoAdministrativoResponse,
    SolicitudRecepcionResponse,
    SolicitudRequisitoAdministrativoResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)
from app.services.gestion_seguimiento.seguimiento_service import (
    validar_presentacion,
    validar_requisito_editable,
)


class SolicitudAdministrativaServiceError(
    Exception
):
    """
    Error base de gestión administrativa.
    """


class SolicitudAdministrativaNoEncontradaError(
    SolicitudAdministrativaServiceError
):
    """
    La solicitud no existe o no está disponible para gestión.
    """


class SolicitudYaRecibidaError(
    SolicitudAdministrativaServiceError
):
    """
    La solicitud ya tiene una recepción registrada.
    """


class SolicitudNoPendienteRecepcionError(
    SolicitudAdministrativaServiceError
):
    """
    La solicitud no puede volver a recibirse.
    """


class SolicitudNoEstaEnRevisionError(
    SolicitudAdministrativaServiceError
):
    """
    La solicitud todavía no se encuentra en revisión.
    """


class RequisitoSolicitudNoEncontradoError(
    SolicitudAdministrativaServiceError
):
    """
    El requisito solicitado no existe.
    """


class RequisitoNoPerteneceSolicitudError(
    SolicitudAdministrativaServiceError
):
    """
    El requisito no pertenece a la solicitud indicada.
    """


class RequisitoEconomicoRequiereApiError(
    SolicitudAdministrativaServiceError
):
    """
    Los requisitos económicos no pueden aprobarse
    manualmente.
    """


# ============================================================
# HELPERS
# ============================================================


def _obtener_solicitud(
    db: Session,
    id_solicitud: int,
):
    solicitud = (
        solicitud_administrativa_repository
        .obtener_solicitud_administrativa_por_id(
            db,
            id_solicitud,
        )
    )

    if solicitud is None:
        raise (
            SolicitudAdministrativaNoEncontradaError(
                "La solicitud no existe o no está "
                "disponible para gestión administrativa."
            )
        )

    return solicitud


def _obtener_documento_identidad(
    db: Session,
    *,
    id_usuario: int,
) -> str | None:
    perfil = (
        seguimiento_repo
        .obtener_perfil(
            db,
            id_usuario,
        )
    )

    if perfil is None:
        return None

    documento = (
        perfil.documento_identidad
    )

    if documento is None:
        return None

    documento_normalizado = (
        documento.strip()
    )

    return (
        documento_normalizado
        or None
    )


def _construir_detalle(
    db: Session,
    id_solicitud: int,
) -> SolicitudAdministrativaDetalleResponse:
    solicitud = _obtener_solicitud(
        db,
        id_solicitud,
    )

    recepcion = (
        solicitud_administrativa_repository
        .obtener_recepcion_por_solicitud(
            db,
            id_solicitud,
        )
    )

    perfil = (
        seguimiento_repo.obtener_perfil(
            db,
            solicitud.id_solicitante,
        )
    )

    resultado = (
        seguimiento_repo.obtener_resultado(
            db,
            id_solicitud,
        )
    )

    entrega = (
        seguimiento_repo.obtener_entrega(
            db,
            id_solicitud,
        )
    )

    return (
        SolicitudAdministrativaDetalleResponse(
            nombre_solicitante=(
                solicitud
                .solicitante
                .nombre_completo
            ),

            perfil_academico=(
                {
                    campo: getattr(
                        perfil,
                        campo,
                    )
                    for campo in (
                        "codigo_estudiante",
                        "sede",
                        "carrera_programa",
                        "nivel_academico",
                        "documento_identidad",
                    )
                }
                if perfil
                else None
            ),

            tipo_finalizacion=(
                solicitud.tipo_finalizacion
            ),

            id_etapa_actual=(
                solicitud.id_etapa_actual
            ),

            etapas=[
                SolicitudEtapaResponse
                .model_validate(
                    etapa
                )
                for etapa
                in seguimiento_repo
                .listar_etapas(
                    db,
                    id_solicitud,
                )
            ],

            observaciones=[
                ObservacionResponse
                .model_validate(
                    observacion
                )
                for observacion
                in seguimiento_repo
                .listar_observaciones(
                    db,
                    id_solicitud,
                )
            ],

            historial=[
                HistorialResponse
                .model_validate(
                    evento
                )
                for evento
                in seguimiento_repo
                .listar_historial(
                    db,
                    id_solicitud,
                )
            ],

            resultado=(
                ResultadoResponse
                .model_validate(
                    resultado
                )
                if resultado
                else None
            ),

            entrega=(
                EntregaResponse
                .model_validate(
                    entrega
                )
                if entrega
                else None
            ),

            pagos=[
                PagoVerificacionResponse
                .model_validate(
                    pago
                )
                .model_dump()
                for pago
                in seguimiento_repo
                .listar_pagos(
                    db,
                    id_solicitud,
                )
            ],

            id_solicitud=(
                solicitud.id_solicitud
            ),

            id_solicitante=(
                solicitud.id_solicitante
            ),

            id_tramite=(
                solicitud.id_tramite
            ),

            nombre_tramite=(
                solicitud
                .nombre_tramite_snapshot
                or solicitud
                .tramite
                .nombre
            ),

            estado=(
                solicitud.estado
            ),

            fecha_creacion=(
                solicitud.fecha_creacion
            ),

            fecha_envio=(
                solicitud.fecha_envio
            ),

            datos=[
                SolicitudDatoAdministrativoResponse
                .model_validate(
                    dato
                )
                for dato
                in solicitud.datos
            ],

            requisitos=[
                SolicitudRequisitoAdministrativoResponse
                .model_validate(
                    requisito
                )
                for requisito
                in sorted(
                    solicitud.requisitos,
                    key=lambda item: (
                        item.orden,
                        item.id_solicitud_requisito,
                    ),
                )
            ],

            recepcion=(
                SolicitudRecepcionResponse
                .model_validate(
                    recepcion
                )
                if recepcion
                is not None
                else None
            ),
        )
    )


# ============================================================
# BANDEJA
# ============================================================


def listar_bandeja_administrativa(
    db: Session,
    *,
    estado: str | None = None,
    id_tramite: int | None = None,
    id_solicitud: int | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    id_solicitante: int | None = None,
    busqueda: str | None = None,
    pagina: int = 1,
    limite: int = 20,
) -> ListaSolicitudesAdministrativasResponse:
    solicitudes, total = (
        solicitud_administrativa_repository
        .listar_solicitudes_administrativas(
            db,
            estado=estado,
            id_tramite=id_tramite,
            id_solicitud=id_solicitud,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            id_solicitante=id_solicitante,
            busqueda=busqueda,
            pagina=pagina,
            limite=limite,
        )
    )

    items: list[
        SolicitudAdministrativaResumenResponse
    ] = []

    for solicitud in solicitudes:
        documento_identidad = (
            _obtener_documento_identidad(
                db,
                id_usuario=(
                    solicitud.id_solicitante
                ),
            )
        )

        items.append(
            SolicitudAdministrativaResumenResponse(
                id_solicitud=(
                    solicitud.id_solicitud
                ),

                id_solicitante=(
                    solicitud.id_solicitante
                ),

                nombre_solicitante=(
                    solicitud
                    .solicitante
                    .nombre_completo
                ),

                documento_identidad=(
                    documento_identidad
                ),

                id_tramite=(
                    solicitud.id_tramite
                ),

                nombre_tramite=(
                    solicitud
                    .nombre_tramite_snapshot
                    or solicitud
                    .tramite
                    .nombre
                ),

                estado=(
                    solicitud.estado
                ),

                fecha_creacion=(
                    solicitud.fecha_creacion
                ),

                fecha_envio=(
                    solicitud.fecha_envio
                ),

                fecha_actualizacion=(
                    getattr(
                        solicitud,
                        "fecha_actualizacion",
                        None,
                    )
                ),
            )
        )

    return (
        ListaSolicitudesAdministrativasResponse(
            items=items,

            total=total,

            pagina=max(
                pagina,
                1,
            ),

            limite=min(
                max(
                    limite,
                    1,
                ),
                100,
            ),
        )
    )


def obtener_detalle_administrativo(
    db: Session,
    *,
    id_solicitud: int,
) -> SolicitudAdministrativaDetalleResponse:
    return _construir_detalle(
        db,
        id_solicitud,
    )


# ============================================================
# RECEPCIÓN
# ============================================================


def recibir_solicitud(
    db: Session,
    *,
    id_solicitud: int,
    id_usuario_receptor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SolicitudAdministrativaDetalleResponse:
    """
    Registra la recepción administrativa inicial.

    Única transición realizada:

        pendiente_recepcion
                ↓
            en_revision
    """
    seguimiento_repo.bloquear_solicitud(
        db,
        id_solicitud,
    )

    solicitud = (
        _obtener_solicitud(
            db,
            id_solicitud,
        )
    )

    if (
        solicitud.estado
        != "pendiente_recepcion"
    ):
        raise (
            SolicitudNoPendienteRecepcionError(
                "La solicitud ya no se encuentra "
                "pendiente de recepción."
            )
        )

    recepcion_existente = (
        solicitud_administrativa_repository
        .obtener_recepcion_por_solicitud(
            db,
            id_solicitud,
        )
    )

    if (
        recepcion_existente
        is not None
    ):
        raise (
            SolicitudYaRecibidaError(
                "La solicitud ya fue recibida."
            )
        )

    fecha_recepcion = (
        datetime.now(
            timezone.utc
        )
    )

    try:
        (
            solicitud_administrativa_repository
            .crear_recepcion(
                db,
                id_solicitud=id_solicitud,
                id_usuario_receptor=(
                    id_usuario_receptor
                ),
                fecha_recepcion=(
                    fecha_recepcion
                ),
            )
        )

        (
            solicitud_administrativa_repository
            .marcar_solicitud_en_revision(
                db,
                solicitud,
            )
        )

        registrar_accion_simple(
            db,
            accion=(
                "recibir_solicitud"
            ),
            modulo=(
                "gestion_seguimiento"
            ),
            id_usuario_actor=(
                id_usuario_receptor
            ),
            entidad="solicitud",
            id_entidad=str(
                id_solicitud
            ),
            exitoso=True,
            detalle={
                "estado_anterior":
                    "pendiente_recepcion",
                "estado_nuevo":
                    "en_revision",
            },
            direccion_ip=(
                direccion_ip
            ),
            user_agent=(
                user_agent
            ),
        )

        seguimiento_repo.registrar_historial(
            db,
            id_solicitud,
            id_usuario_receptor,
            "solicitud_recibida",
            (
                "Solicitud recibida "
                "para revisión."
            ),
        )

        db.commit()

        return _construir_detalle(
            db,
            id_solicitud,
        )

    except IntegrityError as exc:
        db.rollback()

        raise (
            SolicitudYaRecibidaError(
                "La solicitud ya fue recibida."
            )
        ) from exc

    except Exception:
        db.rollback()

        raise


# ============================================================
# VERIFICACIÓN MANUAL DE REQUISITOS NO ECONÓMICOS
# ============================================================


def verificar_requisito_manual(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitud_requisito: int,
    id_usuario_verificador: int,
    datos: RequisitoVerificarRequest,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> RequisitoVerificacionResponse:
    """
    Verifica manualmente un requisito NO económico.

    Los requisitos económicos deben utilizar exclusivamente
    la integración con la API de facturación/pagos.
    """
    seguimiento_repo.bloquear_solicitud(
        db,
        id_solicitud,
    )

    solicitud = (
        _obtener_solicitud(
            db,
            id_solicitud,
        )
    )

    if solicitud.estado not in (
        "en_revision",
        "en_proceso",
    ):
        raise (
            SolicitudNoEstaEnRevisionError(
                "La solicitud debe estar en revisión "
                "antes de verificar sus requisitos."
            )
        )

    requisito = (
        solicitud_administrativa_repository
        .obtener_requisito_solicitud_por_id(
            db,
            id_solicitud_requisito,
        )
    )

    if requisito is None:
        raise (
            RequisitoSolicitudNoEncontradoError(
                "El requisito indicado no existe."
            )
        )

    if (
        requisito.id_solicitud
        != id_solicitud
    ):
        raise (
            RequisitoNoPerteneceSolicitudError(
                "El requisito no pertenece "
                "a la solicitud."
            )
        )

    if requisito.es_economico:
        raise (
            RequisitoEconomicoRequiereApiError(
                "Los requisitos económicos deben "
                "verificarse mediante la API de pagos."
            )
        )

    validar_requisito_editable(
        solicitud,
        requisito,
    )

    if datos.estado == "cumple":
        validar_presentacion(
            requisito
        )

    estado_anterior = (
        requisito.estado_verificacion
    )

    fecha_verificacion = (
        datetime.now(
            timezone.utc
        )
    )

    try:
        requisito = (
            solicitud_administrativa_repository
            .actualizar_verificacion_requisito(
                db,
                requisito,
                estado_verificacion=(
                    datos.estado
                ),
                id_usuario_verificador=(
                    id_usuario_verificador
                ),
                fecha_verificacion=(
                    fecha_verificacion
                ),
                detalle_verificacion=(
                    datos.detalle
                ),
            )
        )

        registrar_accion_simple(
            db,
            accion=(
                "verificar_requisito_solicitud"
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
            exitoso=True,
            detalle={
                "id_solicitud":
                    id_solicitud,

                "estado_anterior":
                    estado_anterior,

                "estado_nuevo":
                    requisito
                    .estado_verificacion,

                "es_economico":
                    False,
            },
            direccion_ip=(
                direccion_ip
            ),
            user_agent=(
                user_agent
            ),
        )

        seguimiento_repo.registrar_historial(
            db,
            id_solicitud,
            id_usuario_verificador,
            "requisito_verificado",
            (
                f"{requisito.nombre}: "
                f"{requisito.estado_verificacion}."
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

        return (
            RequisitoVerificacionResponse
            .model_validate(
                requisito
            )
        )

    except Exception:
        db.rollback()

        raise