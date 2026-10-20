
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import FRONTEND_BASE_URL
from app.models.gestion_seguimiento import (
    SolicitudIntervencion,
    SolicitudNotificacion,
)
from app.repositories.gestion_seguimiento import (
    seguimiento_repository as repo,
    notificacion_repository as notificaciones,
)
from app.services.email.email_service import (
    EmailServiceError,
    construir_html_institucional,
    enviar_correo,
)
from app.services.gestion_seguimiento.seguimiento_service import (
    SeguimientoError,
)


logger = logging.getLogger(__name__)


# ============================================================
# DATOS DE DESTINO
# ============================================================

def _obtener_correo_destino(
    solicitud,
) -> str | None:
    if (
        solicitud.correo_contacto
        and solicitud.correo_contacto.strip()
    ):
        return solicitud.correo_contacto.strip()

    solicitante = solicitud.solicitante

    if solicitante is None:
        return None

    correos = getattr(
        solicitante,
        "correos",
        [],
    )

    principal = next(
        (
            correo
            for correo in correos
            if (
                correo.activo
                and correo.verificado
                and correo.es_principal
            )
        ),
        None,
    )

    if principal is not None:
        return str(principal.correo)

    verificado = next(
        (
            correo
            for correo in correos
            if correo.activo and correo.verificado
        ),
        None,
    )

    if verificado is not None:
        return str(verificado.correo)

    return None


def _obtener_nombre_tramite(
    solicitud,
) -> str:
    if (
        solicitud.nombre_tramite_snapshot
        and solicitud.nombre_tramite_snapshot.strip()
    ):
        return solicitud.nombre_tramite_snapshot.strip()

    if (
        solicitud.tramite is not None
        and solicitud.tramite.nombre
    ):
        return solicitud.tramite.nombre.strip()

    return "Trámite académico"


def _enlace_solicitud(
    id_solicitud: int,
) -> str:
    return (
        f"{FRONTEND_BASE_URL}"
        f"/solicitudes/{id_solicitud}"
    )


# ============================================================
# CONTENIDO DE RESULTADOS
# ============================================================

def _construir_notificacion(
    solicitud,
) -> tuple[str, str, str]:
    numero = solicitud.id_solicitud
    nombre = _obtener_nombre_tramite(solicitud)
    referencia = f"Solicitud #{numero} — {nombre}"
    enlace = _enlace_solicitud(numero)

    if solicitud.tipo_finalizacion == "entrega":
        asunto = (
            f"Documento listo para recoger "
            f"— Solicitud #{numero}"
        )

        titulo = "Tu documento está listo para recoger"

        parrafos = [
            (
                "El documento correspondiente a tu trámite "
                "académico se encuentra disponible para "
                "su recojo."
            ),
            (
                "Consulta el seguimiento de tu solicitud "
                "para revisar las indicaciones registradas "
                "por el personal administrativo."
            ),
        ]

        aviso = (
            "Este aviso corresponde a la disponibilidad "
            "del documento. Si necesitas confirmar el lugar "
            "o las condiciones del recojo, consulta con "
            "la unidad responsable del trámite."
        )

    else:
        asunto = (
            f"Trámite finalizado "
            f"— Solicitud #{numero}"
        )

        titulo = "Tu trámite ha finalizado"

        parrafos = [
            (
                "La atención de tu trámite académico "
                "ha finalizado."
            ),
            (
                "Ingresa al seguimiento de tu solicitud "
                "para consultar el resultado y las "
                "indicaciones que haya registrado "
                "el personal administrativo."
            ),
        ]

        aviso = (
            "Este mensaje informa la conclusión "
            "de la atención registrada en el sistema."
        )

    texto = (
        f"{titulo}\n\n"
        f"{referencia}\n\n"
        + "\n\n".join(parrafos)
        + f"\n\nConsultar solicitud:\n{enlace}\n\n"
        + aviso
    )

    html = construir_html_institucional(
        titulo=titulo,
        referencia=referencia,
        parrafos=parrafos,
        texto_accion="Consultar mi solicitud",
        url_accion=enlace,
        aviso=aviso,
    )

    return asunto, texto, html


# ============================================================
# CONTENIDO DE CONVOCATORIAS
# ============================================================

def _html_convocatoria(
    notificacion: SolicitudNotificacion,
) -> str:
    """
    Presenta el texto ya registrado para una convocatoria.

    No cambia el texto persistido ni reconstruye los datos
    históricos de la intervención.
    """

    lineas = (
        notificacion.contenido_texto
        or ""
    ).splitlines()

    referencia = (
        " — ".join(
            linea.strip()
            for linea in lineas[:2]
            if linea.strip()
        )
        or f"Solicitud #{notificacion.id_solicitud}"
    )

    descripcion = "\n".join(
        linea.strip()
        for linea in lineas[2:]
        if linea.strip()
    )

    parrafos = [
        descripcion
        or "Tienes una convocatoria presencial relacionada con tu trámite.",
    ]

    return construir_html_institucional(
        titulo="Convocatoria presencial",
        referencia=referencia,
        parrafos=parrafos,
        texto_accion="Consultar mi solicitud",
        url_accion=_enlace_solicitud(
            notificacion.id_solicitud
        ),
        aviso=(
            "Revisa el seguimiento de tu solicitud. "
            "Este aviso no constituye una confirmación "
            "de una cita con fecha u hora determinada."
        ),
    )


# ============================================================
# ENVÍO PERSISTENTE
# ============================================================

def _enviar_notificacion_registrada(
    db: Session,
    id_notificacion: int,
) -> bool:
    """
    Bloquea el registro durante el intento de envío.

    Una notificación aceptada por Brevo no vuelve a
    enviarse desde este servicio.

    Un timeout puede dejar incierto si Brevo recibió
    el mensaje.
    """

    try:
        notificacion = db.scalar(
            select(SolicitudNotificacion)
            .where(
                SolicitudNotificacion.id_notificacion
                == id_notificacion
            )
            .with_for_update()
        )

        if notificacion is None:
            db.rollback()
            return False

        if notificacion.estado == "enviado":
            db.commit()
            return True

        html = None

        if notificacion.tipo == "resultado":
            solicitud = repo.obtener_solicitud_completa(
                db,
                notificacion.id_solicitud,
            )

            if solicitud is None:
                db.rollback()
                return False

            _, _, html = _construir_notificacion(
                solicitud
            )

        elif notificacion.tipo == "convocatoria":
            html = _html_convocatoria(
                notificacion
            )

        try:
            enviar_correo(
                destinatario=notificacion.destinatario,
                asunto=notificacion.asunto,
                contenido_texto=notificacion.contenido_texto,
                contenido_html=html,
            )

        except EmailServiceError as exc:
            notificaciones.registrar_intento(
                db,
                notificacion,
                enviado=False,
                error=str(exc),
            )

            db.commit()

            logger.warning(
                "Falló el correo de la notificación %s: %s",
                id_notificacion,
                exc,
            )

            return False

        notificaciones.registrar_intento(
            db,
            notificacion,
            enviado=True,
        )

        db.commit()

        logger.info(
            "Brevo aceptó la notificación %s.",
            id_notificacion,
        )

        return True

    except Exception:
        db.rollback()
        logger.exception(
            "Error al procesar la notificación %s.",
            id_notificacion,
        )
        raise


# ============================================================
# CONVOCATORIAS
# ============================================================

def notificar_convocatoria(
    db: Session,
    id_intervencion: int,
) -> bool:
    notificacion = (
        notificaciones.obtener_convocatoria(
            db,
            id_intervencion,
        )
    )

    if notificacion is None:
        return False

    return _enviar_notificacion_registrada(
        db,
        notificacion.id_notificacion,
    )


# ============================================================
# RESULTADOS
# ============================================================

def notificar_resultado_solicitud(
    db: Session,
    id_solicitud: int,
) -> bool:
    """
    Registra y envía el aviso después de confirmar
    el resultado administrativo.

    Un fallo de Brevo no revierte el resultado.
    """

    solicitud = repo.obtener_solicitud_completa(
        db,
        id_solicitud,
    )

    if solicitud is None:
        logger.warning(
            "Solicitud %s inexistente al notificar.",
            id_solicitud,
        )
        return False

    if solicitud.estado not in {
        "lista_para_entrega",
        "finalizada",
    }:
        return False

    existente = notificaciones.obtener_resultado(
        db,
        id_solicitud,
    )

    if existente is not None:
        return _enviar_notificacion_registrada(
            db,
            existente.id_notificacion,
        )

    destinatario = _obtener_correo_destino(
        solicitud
    )

    if destinatario is None:
        logger.warning(
            "La solicitud %s no tiene correo de destino.",
            id_solicitud,
        )
        return False

    asunto, texto, _ = _construir_notificacion(
        solicitud
    )

    try:
        notificacion = notificaciones.crear(
            db,
            id_solicitud=id_solicitud,
            tipo="resultado",
            destinatario=destinatario,
            asunto=asunto,
            contenido_texto=texto,
        )

        id_notificacion = (
            notificacion.id_notificacion
        )

        db.commit()

    except IntegrityError:
        db.rollback()

        existente = notificaciones.obtener_resultado(
            db,
            id_solicitud,
        )

        if existente is None:
            raise

        id_notificacion = (
            existente.id_notificacion
        )

    return _enviar_notificacion_registrada(
        db,
        id_notificacion,
    )


# ============================================================
# REINTENTO ADMINISTRATIVO
# ============================================================

def reintentar_notificacion(
    db: Session,
    *,
    id_solicitud: int,
    id_notificacion: int,
) -> SolicitudNotificacion:
    """
    Reintenta una notificación existente.

    No crea otra convocatoria ni otro resultado.
    """

    notificacion = db.scalar(
        select(SolicitudNotificacion)
        .where(
            SolicitudNotificacion.id_notificacion
            == id_notificacion,
            SolicitudNotificacion.id_solicitud
            == id_solicitud,
        )
    )

    if notificacion is None:
        raise SeguimientoError(
            "La notificación no existe.",
            404,
        )

    if notificacion.estado == "enviado":
        return notificacion

    solicitud = repo.obtener_solicitud_completa(
        db,
        id_solicitud,
    )

    if solicitud is None:
        raise SeguimientoError(
            "La solicitud no existe.",
            404,
        )

    if notificacion.tipo == "convocatoria":
        intervencion = db.get(
            SolicitudIntervencion,
            notificacion.id_intervencion,
        )

        if (
            intervencion is None
            or intervencion.id_solicitud != id_solicitud
            or intervencion.estado != "convocada"
            or solicitud.estado != "en_proceso"
        ):
            raise SeguimientoError(
                "Esta convocatoria ya no puede enviarse."
            )

    elif notificacion.tipo == "resultado":
        if solicitud.estado not in {
            "lista_para_entrega",
            "finalizada",
        }:
            raise SeguimientoError(
                "El resultado todavía no puede notificarse."
            )

    id_registro = notificacion.id_notificacion

    _enviar_notificacion_registrada(
        db,
        id_registro,
    )

    return db.get(
        SolicitudNotificacion,
        id_registro,
    )
