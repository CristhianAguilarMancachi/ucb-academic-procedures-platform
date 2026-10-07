from __future__ import annotations

import logging
from html import escape

from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento import (
    seguimiento_repository as repo,
)
from app.services.email.email_service import (
    EmailServiceError,
    enviar_correo,
)


logger = logging.getLogger(__name__)


def _obtener_correo_destino(
    solicitud,
) -> str | None:
    """
    Obtiene el correo al que deben enviarse las
    notificaciones de una solicitud.

    Se prioriza el correo de contacto indicado
    expresamente para la solicitud.

    Si no existe, se utiliza el correo activo y
    verificado de la cuenta del solicitante.
    """
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

    correo_principal = next(
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

    if correo_principal is not None:
        return str(
            correo_principal.correo
        )

    correo_verificado = next(
        (
            correo
            for correo in correos
            if (
                correo.activo
                and correo.verificado
            )
        ),
        None,
    )

    if correo_verificado is not None:
        return str(
            correo_verificado.correo
        )

    return None


def _obtener_nombre_tramite(
    solicitud,
) -> str:
    if (
        solicitud.nombre_tramite_snapshot
        and solicitud.nombre_tramite_snapshot.strip()
    ):
        return (
            solicitud.nombre_tramite_snapshot
            .strip()
        )

    if (
        solicitud.tramite is not None
        and solicitud.tramite.nombre
    ):
        return solicitud.tramite.nombre.strip()

    return "Trámite académico"


def _construir_notificacion(
    solicitud,
) -> tuple[str, str, str]:
    """
    Construye asunto, texto y HTML según la modalidad
    de finalización de la solicitud.
    """
    id_solicitud = (
        solicitud.id_solicitud
    )

    nombre_tramite = (
        _obtener_nombre_tramite(
            solicitud
        )
    )

    if (
        solicitud.tipo_finalizacion
        == "entrega"
    ):
        asunto = (
            f"Solicitud #{id_solicitud} "
            "lista para recojo"
        )

        contenido_texto = (
            f"Solicitud #{id_solicitud}\n"
            f"{nombre_tramite}\n\n"
            "Tu trámite se encuentra listo.\n\n"
            "Puedes pasar por Kardex / Dirección Académica "
            "para realizar el recojo correspondiente.\n\n"
            "Puedes consultar el seguimiento de tu solicitud "
            "desde el Sistema de Trámites Académicos."
        )

        contenido_html = f"""
        <html>
          <body>
            <h2>Tu trámite está listo</h2>

            <p>
              <strong>Solicitud #{id_solicitud}</strong>
            </p>

            <p>
              {escape(nombre_tramite)}
            </p>

            <p>
              Tu trámite se encuentra listo para recojo.
            </p>

            <p>
              Puedes pasar por
              <strong>Kardex / Dirección Académica</strong>
              para realizar el recojo correspondiente.
            </p>

            <p>
              Puedes consultar el seguimiento de tu solicitud
              desde el Sistema de Trámites Académicos.
            </p>
          </body>
        </html>
        """

        return (
            asunto,
            contenido_texto,
            contenido_html,
        )

    asunto = (
        f"Solicitud #{id_solicitud} "
        "finalizada"
    )

    contenido_texto = (
        f"Solicitud #{id_solicitud}\n"
        f"{nombre_tramite}\n\n"
        "Tu trámite ha finalizado.\n\n"
        "Ingresa al Sistema de Trámites Académicos "
        "para revisar el resultado y las indicaciones "
        "registradas para tu solicitud."
    )

    contenido_html = f"""
    <html>
      <body>
        <h2>Tu trámite ha finalizado</h2>

        <p>
          <strong>Solicitud #{id_solicitud}</strong>
        </p>

        <p>
          {escape(nombre_tramite)}
        </p>

        <p>
          El procesamiento de tu trámite ha finalizado.
        </p>

        <p>
          Ingresa al Sistema de Trámites Académicos
          para revisar el resultado y las indicaciones
          registradas para tu solicitud.
        </p>
      </body>
    </html>
    """

    return (
        asunto,
        contenido_texto,
        contenido_html,
    )


def notificar_resultado_solicitud(
    db: Session,
    id_solicitud: int,
) -> bool:
    """
    Envía la notificación correspondiente después de que
    el resultado de la solicitud ya fue confirmado en BDD.

    Un fallo del servicio de correo nunca revierte ni
    modifica el estado de la solicitud.
    """
    solicitud = (
        repo.obtener_solicitud_completa(
            db,
            id_solicitud,
        )
    )

    if solicitud is None:
        logger.warning(
            "No se pudo notificar la solicitud %s: "
            "no fue encontrada.",
            id_solicitud,
        )
        return False

    if solicitud.estado not in {
        "lista_para_entrega",
        "finalizada",
    }:
        return False

    destinatario = (
        _obtener_correo_destino(
            solicitud
        )
    )

    if destinatario is None:
        logger.warning(
            "No se pudo notificar la solicitud %s: "
            "no existe un correo disponible.",
            id_solicitud,
        )
        return False

    (
        asunto,
        contenido_texto,
        contenido_html,
    ) = _construir_notificacion(
        solicitud
    )

    try:
        enviar_correo(
            destinatario=destinatario,
            asunto=asunto,
            contenido_texto=contenido_texto,
            contenido_html=contenido_html,
        )

    except EmailServiceError:
        logger.exception(
            "No fue posible enviar la notificación "
            "de finalización de la solicitud %s.",
            id_solicitud,
        )
        return False

    logger.info(
        "Notificación de finalización enviada "
        "para la solicitud %s.",
        id_solicitud,
    )

    return True