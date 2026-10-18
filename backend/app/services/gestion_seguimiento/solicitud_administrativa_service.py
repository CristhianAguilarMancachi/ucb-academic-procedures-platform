
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento import (
    seguimiento_repository as seguimiento_repo,
    solicitud_administrativa_repository as admin_repo,
)

from app.schemas.gestion_seguimiento.pago_verificacion import (
    PagoVerificacionResponse,
)

from app.schemas.gestion_seguimiento.seguimiento import (
    HistorialResponse,
    ObservacionResponse,
    ResultadoResponse,
)

from app.schemas.gestion_seguimiento.solicitud_administrativa import (
    ListaSolicitudesAdministrativasResponse,
    RequisitoVerificacionResponse,
    RequisitoVerificarRequest,
    RequisitosAdministrativosConfirmarRequest,
    RequisitosAdministrativosConfirmarResponse,
    SolicitudAdministrativaDetalleResponse,
    SolicitudAdministrativaResumenResponse,
    SolicitudDatoAdministrativoResponse,
    SolicitudRecepcionResponse,
    SolicitudRequisitoAdministrativoResponse,
)

from app.services.auth.audit_service import (
    registrar_accion_simple,
)

from app.services.gestion_seguimiento import (
    atencion_service,
)

from app.services.gestion_seguimiento.seguimiento_service import (
    SeguimientoError,
    validar_presentacion,
    validar_requisito_editable,
)


# ============================================================
# ERRORES
# ============================================================

class SolicitudAdministrativaServiceError(Exception):
    """Error base de gestión administrativa."""


class SolicitudAdministrativaNoEncontradaError(
    SolicitudAdministrativaServiceError
):
    """Solicitud inexistente o no disponible."""


class SolicitudYaRecibidaError(
    SolicitudAdministrativaServiceError
):
    """La solicitud ya cuenta con recepción."""


class SolicitudNoPendienteRecepcionError(
    SolicitudAdministrativaServiceError
):
    """La solicitud no está pendiente de recepción."""


class SolicitudNoEstaEnRevisionError(
    SolicitudAdministrativaServiceError
):
    """La solicitud no está en atención."""


class RequisitoSolicitudNoEncontradoError(
    SolicitudAdministrativaServiceError
):
    """Requisito inexistente."""


class RequisitoNoPerteneceSolicitudError(
    SolicitudAdministrativaServiceError
):
    """El requisito pertenece a otra solicitud."""


class RequisitoEconomicoRequiereApiError(
    SolicitudAdministrativaServiceError
):
    """Los requisitos económicos requieren la API de pagos."""


class RequisitoNoEsAdministrativoError(
    SolicitudAdministrativaServiceError
):
    """El requisito no admite confirmación administrativa."""


class RequisitoAdministrativoYaConfirmadoError(
    SolicitudAdministrativaServiceError
):
    """El requisito ya fue confirmado."""


# ============================================================
# CONSULTAS INTERNAS
# ============================================================

def _obtener_solicitud(
    db: Session,
    id_solicitud: int,
):
    solicitud = (
        admin_repo.obtener_solicitud_administrativa_por_id(
            db,
            id_solicitud,
        )
    )

    if solicitud is None:
        raise SolicitudAdministrativaNoEncontradaError(
            "La solicitud no existe o no está disponible "
            "para gestión administrativa."
        )

    return solicitud


def _obtener_documento_identidad(
    db: Session,
    *,
    id_usuario: int,
) -> str | None:
    perfil = seguimiento_repo.obtener_perfil(
        db,
        id_usuario,
    )

    if perfil is None:
        return None

    documento = perfil.documento_identidad

    if documento is None:
        return None

    return documento.strip() or None


# ============================================================
# DETALLE ADMINISTRATIVO
# ============================================================

def _construir_detalle(
    db: Session,
    id_solicitud: int,
) -> SolicitudAdministrativaDetalleResponse:
    solicitud = _obtener_solicitud(
        db,
        id_solicitud,
    )

    recepcion = admin_repo.obtener_recepcion_por_solicitud(
        db,
        id_solicitud,
    )

    perfil = seguimiento_repo.obtener_perfil(
        db,
        solicitud.id_solicitante,
    )

    resultado = seguimiento_repo.obtener_resultado(
        db,
        id_solicitud,
    )

    datos = [
        SolicitudDatoAdministrativoResponse.model_validate(
            dato
        )
        for dato in solicitud.datos
    ]

    requisitos = [
        SolicitudRequisitoAdministrativoResponse.model_validate(
            requisito
        )
        for requisito in sorted(
            solicitud.requisitos,
            key=lambda item: (
                item.orden,
                item.id_solicitud_requisito,
            ),
        )
    ]

    observaciones = [
        ObservacionResponse.model_validate(
            observacion
        )
        for observacion in seguimiento_repo.listar_observaciones(
            db,
            id_solicitud,
        )
    ]

    historial = [
        HistorialResponse.model_validate(
            registro
        )
        for registro in seguimiento_repo.listar_historial(
            db,
            id_solicitud,
        )
    ]

    pagos = [
        PagoVerificacionResponse.model_validate(
            pago
        ).model_dump()
        for pago in seguimiento_repo.listar_pagos(
            db,
            id_solicitud,
        )
    ]

    perfil_academico = None

    if perfil is not None:
        perfil_academico = {
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

    return SolicitudAdministrativaDetalleResponse(
        id_solicitud=solicitud.id_solicitud,
        id_solicitante=solicitud.id_solicitante,
        id_tramite=solicitud.id_tramite,

        nombre_tramite=(
            solicitud.nombre_tramite_snapshot
            or solicitud.tramite.nombre
        ),

        nombre_solicitante=(
            solicitud.solicitante.nombre_completo
        ),

        estado=solicitud.estado,

        tipo_finalizacion=solicitud.tipo_finalizacion,
        tipo_intervencion=solicitud.tipo_intervencion,

        fecha_creacion=solicitud.fecha_creacion,
        fecha_envio=solicitud.fecha_envio,

        perfil_academico=perfil_academico,

        datos=datos,
        requisitos=requisitos,

        recepcion=(
            SolicitudRecepcionResponse.model_validate(
                recepcion
            )
            if recepcion is not None
            else None
        ),

        observaciones=observaciones,
        historial=historial,

        resultado=(
            ResultadoResponse.model_validate(
                resultado
            )
            if resultado is not None
            else None
        ),

        pagos=pagos,

        # No se utilizan etapas de solicitud.
    )


# ============================================================
# BANDEJA ADMINISTRATIVA
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
        admin_repo.listar_solicitudes_administrativas(
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

    items = []

    for solicitud in solicitudes:
        documento_identidad = _obtener_documento_identidad(
            db,
            id_usuario=solicitud.id_solicitante,
        )

        items.append(
            SolicitudAdministrativaResumenResponse(
                id_solicitud=solicitud.id_solicitud,
                id_solicitante=solicitud.id_solicitante,

                nombre_solicitante=(
                    solicitud.solicitante.nombre_completo
                ),

                documento_identidad=documento_identidad,

                id_tramite=solicitud.id_tramite,

                nombre_tramite=(
                    solicitud.nombre_tramite_snapshot
                    or solicitud.tramite.nombre
                ),

                estado=solicitud.estado,
                tipo_intervencion=solicitud.tipo_intervencion,

                fecha_creacion=solicitud.fecha_creacion,
                fecha_envio=solicitud.fecha_envio,

                fecha_actualizacion=(
                    solicitud.fecha_actualizacion
                ),
            )
        )

    return ListaSolicitudesAdministrativasResponse(
        items=items,
        total=total,
        pagina=max(pagina, 1),
        limite=min(max(limite, 1), 100),
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
# RECEPCIÓN E INICIO DE ATENCIÓN
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
    Compatibilidad con el endpoint administrativo
    de recepción.

    Recibir equivale a iniciar la atención.

    No crea etapas, no exige verificar requisitos
    y no genera el estado en_revision.
    """

    solicitud = _obtener_solicitud(
        db,
        id_solicitud,
    )

    if solicitud.estado != "pendiente_recepcion":
        raise SolicitudNoPendienteRecepcionError(
            "La solicitud ya no está pendiente "
            "de recepción."
        )

    recepcion = admin_repo.obtener_recepcion_por_solicitud(
        db,
        id_solicitud,
    )

    if recepcion is not None:
        raise SolicitudYaRecibidaError(
            "La solicitud ya tiene recepción registrada."
        )

    try:
        atencion_service.iniciar_atencion(
            db,
            id_solicitud,
            id_usuario_receptor,
        )

    except SeguimientoError as exc:
        raise SolicitudNoPendienteRecepcionError(
            str(exc)
        ) from exc

    return _construir_detalle(
        db,
        id_solicitud,
    )


# ============================================================
# VERIFICACIÓN MANUAL EXISTENTE
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
    Conserva la compatibilidad con el endpoint de
    verificación manual.

    Los documentos físicos se completan durante su
    recepción y los económicos mediante la API.

    Este endpoint queda limitado a requisitos
    administrativos no físicos ni económicos.
    """

    seguimiento_repo.bloquear_solicitud(
        db,
        id_solicitud,
    )

    solicitud = _obtener_solicitud(
        db,
        id_solicitud,
    )

    if solicitud.estado not in (
        "en_revision",
        "en_proceso",
    ):
        raise SolicitudNoEstaEnRevisionError(
            "La solicitud debe estar en atención "
            "para verificar sus requisitos."
        )

    requisito = admin_repo.obtener_requisito_solicitud_por_id(
        db,
        id_solicitud_requisito,
    )

    if requisito is None:
        raise RequisitoSolicitudNoEncontradoError(
            "El requisito indicado no existe."
        )

    if requisito.id_solicitud != id_solicitud:
        raise RequisitoNoPerteneceSolicitudError(
            "El requisito no pertenece a la solicitud."
        )

    if requisito.es_economico:
        raise RequisitoEconomicoRequiereApiError(
            "Los requisitos económicos deben "
            "verificarse mediante la API de pagos."
        )

    if requisito.requiere_presentacion_fisica:
        raise RequisitoNoEsAdministrativoError(
            "Los documentos físicos se completan "
            "al registrar su recepción."
        )

    validar_requisito_editable(
        solicitud,
        requisito,
    )

    estado_anterior = requisito.estado_verificacion

    try:
        requisito = admin_repo.actualizar_verificacion_requisito(
            db,
            requisito,
            estado_verificacion=datos.estado,
            id_usuario_verificador=id_usuario_verificador,
            fecha_verificacion=datetime.now(timezone.utc),
            detalle_verificacion=datos.detalle,
        )

        registrar_accion_simple(
            db,
            accion="verificar_requisito_solicitud",
            modulo="gestion_seguimiento",
            id_usuario_actor=id_usuario_verificador,
            entidad="solicitud_requisito",
            id_entidad=str(
                requisito.id_solicitud_requisito
            ),
            exitoso=True,
            detalle={
                "id_solicitud": id_solicitud,
                "estado_anterior": estado_anterior,
                "estado_nuevo": requisito.estado_verificacion,
                "es_economico": False,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
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
            id_solicitud_requisito=(
                requisito.id_solicitud_requisito
            ),
        )

        db.commit()

        return RequisitoVerificacionResponse.model_validate(
            requisito
        )

    except Exception:
        db.rollback()
        raise


# ============================================================
# CONFIRMACIÓN AGRUPADA DE REQUISITOS ADMINISTRATIVOS
# ============================================================

def confirmar_requisitos_administrativos(
    db: Session,
    *,
    id_solicitud: int,
    id_usuario_verificador: int,
    datos: RequisitosAdministrativosConfirmarRequest,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> RequisitosAdministrativosConfirmarResponse:
    """
    Confirma los requisitos administrativos seleccionados
    desde la pestaña Requisitos.

    La operación es atómica:
    - valida todos los identificadores;
    - impide incluir documentos físicos y pagos;
    - impide confirmar requisitos ya cumplidos;
    - registra verificador y fecha;
    - incorpora historial y auditoría;
    - confirma los cambios en una sola transacción.

    No modifica el estado de la solicitud ni ejecuta
    etapas institucionales.
    """

    try:
        seguimiento_repo.bloquear_solicitud(
            db,
            id_solicitud,
        )

        solicitud = _obtener_solicitud(
            db,
            id_solicitud,
        )

        if solicitud.estado not in (
            "en_revision",
            "en_proceso",
        ):
            raise SolicitudNoEstaEnRevisionError(
                "La solicitud debe estar en atención "
                "para confirmar requisitos administrativos."
            )

        ids_solicitados = set(datos.ids_requisitos)

        requisitos = [
            requisito
            for requisito in solicitud.requisitos
            if requisito.id_solicitud_requisito
            in ids_solicitados
        ]

        if len(requisitos) != len(ids_solicitados):
            raise RequisitoNoPerteneceSolicitudError(
                "Uno o más requisitos no pertenecen "
                "a esta solicitud."
            )

        # Se valida toda la selección antes de actualizar
        # cualquier requisito.
        for requisito in requisitos:
            validar_requisito_editable(
                solicitud,
                requisito,
            )

            if requisito.es_economico:
                raise RequisitoEconomicoRequiereApiError(
                    "Los pagos deben validarse mediante "
                    "la API de facturación."
                )

            if requisito.requiere_presentacion_fisica:
                raise RequisitoNoEsAdministrativoError(
                    "La documentación física se completa "
                    "al registrar su recepción."
                )

            if requisito.estado_verificacion == "cumple":
                raise RequisitoAdministrativoYaConfirmadoError(
                    f'El requisito "{requisito.nombre}" '
                    "ya está confirmado."
                )

        fecha = datetime.now(timezone.utc)

        ids_confirmados: list[int] = []

        for requisito in sorted(
            requisitos,
            key=lambda item: (
                item.orden,
                item.id_solicitud_requisito,
            ),
        ):
            estado_anterior = requisito.estado_verificacion

            admin_repo.actualizar_verificacion_requisito(
                db,
                requisito,
                estado_verificacion="cumple",
                id_usuario_verificador=id_usuario_verificador,
                fecha_verificacion=fecha,
                detalle_verificacion=(
                    datos.detalle
                    or "Cumplimiento confirmado por personal administrativo."
                ),
            )

            seguimiento_repo.registrar_historial(
                db,
                id_solicitud,
                id_usuario_verificador,
                "requisito_administrativo_confirmado",
                (
                    "Cumplimiento administrativo confirmado: "
                    f"{requisito.nombre}."
                ),
                id_solicitud_requisito=(
                    requisito.id_solicitud_requisito
                ),
            )

            registrar_accion_simple(
                db,
                accion="confirmar_requisito_administrativo",
                modulo="gestion_seguimiento",
                id_usuario_actor=id_usuario_verificador,
                entidad="solicitud_requisito",
                id_entidad=str(
                    requisito.id_solicitud_requisito
                ),
                exitoso=True,
                detalle={
                    "id_solicitud": id_solicitud,
                    "estado_anterior": estado_anterior,
                    "estado_nuevo": "cumple",
                    "tipo": "administrativo",
                },
                direccion_ip=direccion_ip,
                user_agent=user_agent,
            )

            ids_confirmados.append(
                requisito.id_solicitud_requisito
            )

        db.commit()

        return RequisitosAdministrativosConfirmarResponse(
            mensaje=(
                "Se confirmó el cumplimiento de "
                f"{len(ids_confirmados)} requisito(s) "
                "administrativo(s)."
            ),
            id_solicitud=id_solicitud,
            requisitos_confirmados=ids_confirmados,
            cantidad_confirmada=len(ids_confirmados),
        )

    except Exception:
        db.rollback()
        raise
