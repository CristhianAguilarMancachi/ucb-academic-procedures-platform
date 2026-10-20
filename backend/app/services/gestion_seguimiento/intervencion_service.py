
from __future__ import annotations

from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento import (
    intervencion_repository as intervenciones,
    notificacion_repository as notificaciones,
    seguimiento_repository as seguimiento_repo,
)
from app.schemas.gestion_seguimiento.intervencion import (
    RevisionPresencialRequest,
)
from app.services.gestion_seguimiento.notificacion_solicitud_service import (
    _obtener_correo_destino,
)
from app.services.gestion_seguimiento.seguimiento_service import (
    SeguimientoError,
    evento,
    exigir_estado,
    exigir_requisitos,
    exigir_sin_observaciones,
    obtener_para_accion,
    transaccion,
)


# ============================================================
# VALIDACIONES COMUNES
# ============================================================

def _tipo_solicitud(solicitud) -> str:
    tipo = solicitud.tipo_intervencion

    if tipo not in ("conformidad", "firma"):
        raise SeguimientoError(
            "Este trámite no requiere una "
            "intervención presencial."
        )

    return tipo


def _buscar_resolucion(
    db: Session,
    id_solicitud: int,
):
    return next(
        (
            registro
            for registro in seguimiento_repo.listar_historial(
                db,
                id_solicitud,
            )
            if registro.evento == "resolucion_emitida"
        ),
        None,
    )


def _respuesta_resolucion(registro) -> dict:
    return {
        "id_historial": registro.id_historial,
        "id_solicitud": registro.id_solicitud,
        "id_usuario_actor": registro.id_usuario_actor,
        "fecha_emision": registro.fecha_evento,
        "detalle": registro.detalle,
    }


# ============================================================
# RESOLUCIÓN INSTITUCIONAL
# ============================================================

def consultar_resolucion(
    db: Session,
    id_solicitud: int,
) -> dict | None:
    solicitud = seguimiento_repo.obtener_solicitud_completa(
        db,
        id_solicitud,
    )

    if solicitud is None:
        raise SeguimientoError(
            "La solicitud no existe.",
            404,
        )

    if solicitud.tipo_intervencion != "firma":
        raise SeguimientoError(
            "Este trámite no requiere "
            "emisión de resolución previa."
        )

    registro = _buscar_resolucion(
        db,
        id_solicitud,
    )

    return (
        _respuesta_resolucion(registro)
        if registro is not None
        else None
    )


@transaccion
def registrar_resolucion_emitida(
    db: Session,
    id_solicitud: int,
    actor: int,
) -> dict:
    """
    El administrativo confirma que la resolución
    institucional ya fue efectivamente emitida.

    No genera el documento ni simula su emisión.
    Registra el hecho con actor y fecha de servidor.
    """
    solicitud = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        solicitud,
        "en_proceso",
    )

    if _tipo_solicitud(solicitud) != "firma":
        raise SeguimientoError(
            "La emisión previa solo corresponde "
            "a trámites con firma de resolución."
        )

    if _buscar_resolucion(db, id_solicitud):
        raise SeguimientoError(
            "La emisión de la resolución "
            "ya fue registrada."
        )

    if intervenciones.obtener_ultima(
        db,
        id_solicitud,
    ) is not None:
        raise SeguimientoError(
            "No puede registrarse la emisión "
            "después de una convocatoria."
        )

    exigir_sin_observaciones(
        db,
        id_solicitud,
    )

    exigir_requisitos(
        solicitud.requisitos,
    )

    evento(
        db,
        solicitud,
        actor,
        "resolucion_emitida",
        (
            "El personal administrativo confirmó "
            "la emisión de la resolución institucional. "
            "Queda pendiente la firma presencial "
            "del estudiante."
        ),
    )

    registro = _buscar_resolucion(
        db,
        id_solicitud,
    )

    if registro is None:
        raise SeguimientoError(
            "No pudo recuperarse el registro "
            "de emisión de la resolución.",
            500,
        )

    return _respuesta_resolucion(registro)


# ============================================================
# CONVOCATORIAS
# ============================================================

def _texto_convocatoria(
    solicitud,
    tipo: str,
) -> tuple[str, str]:
    numero = solicitud.id_solicitud

    nombre = (
        solicitud.nombre_tramite_snapshot
        or (
            solicitud.tramite.nombre
            if solicitud.tramite is not None
            else None
        )
        or "Trámite académico"
    )

    if tipo == "conformidad":
        asunto = (
            f"Revisión presencial de convalidación "
            f"— Solicitud #{numero}"
        )

        titulo = (
            "Convocatoria para revisión de convalidación"
        )

        instruccion = (
            "Debes acudir a Dirección Académica "
            "de la UCB — Sede La Paz para revisar "
            "la propuesta de convalidación y "
            "expresar tu conformidad o comunicar "
            "las observaciones que correspondan."
        )

    else:
        asunto = (
            f"Firma presencial de resolución "
            f"— Solicitud #{numero}"
        )

        titulo = (
            "Convocatoria para firma de resolución"
        )

        instruccion = (
            "Debes acudir a Dirección Académica "
            "de la UCB — Sede La Paz para realizar "
            "la firma presencial de la resolución "
            "institucional emitida para tu trámite."
        )

    texto = (
        f"{titulo}\n\n"
        f"Solicitud #{numero}\n"
        f"{nombre}\n\n"
        "Tu trámite requiere una intervención presencial "
        "para continuar su atención.\n\n"
        f"{instruccion}\n\n"
        "Consulta el seguimiento de tu solicitud "
        "en el Sistema de Trámites Académicos "
        "para revisar la información registrada.\n\n"
        "Este mensaje no establece una fecha ni una "
        "hora específica de atención."
    )

    return asunto, texto


@transaccion
def convocar(
    db: Session,
    id_solicitud: int,
    actor: int,
):
    solicitud = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        solicitud,
        "en_proceso",
    )

    exigir_sin_observaciones(
        db,
        id_solicitud,
    )

    tipo = _tipo_solicitud(solicitud)

    # No permite convocar a firmar una resolución
    # cuya emisión todavía no fue registrada.
    if (
        tipo == "firma"
        and _buscar_resolucion(
            db,
            id_solicitud,
        ) is None
    ):
        raise SeguimientoError(
            "Primero debe registrarse la emisión "
            "de la resolución institucional."
        )

    anterior = intervenciones.obtener_ultima(
        db,
        id_solicitud,
    )

    if (
        anterior is not None
        and anterior.estado not in (
            "no_conforme",
            "anulada",
        )
    ):
        raise SeguimientoError(
            "Ya existe una convocatoria pendiente "
            "o una intervención completada."
        )

    destinatario = _obtener_correo_destino(
        solicitud
    )

    if destinatario is None:
        raise SeguimientoError(
            "La solicitud no tiene un correo "
            "disponible para la convocatoria."
        )

    intervencion = intervenciones.crear_convocatoria(
        db,
        id_solicitud=id_solicitud,
        tipo=tipo,
        actor=actor,
    )

    asunto, contenido = _texto_convocatoria(
        solicitud,
        tipo,
    )

    notificacion = notificaciones.crear(
        db,
        id_solicitud=id_solicitud,
        id_intervencion=(
            intervencion.id_intervencion
        ),
        tipo="convocatoria",
        destinatario=destinatario,
        asunto=asunto,
        contenido_texto=contenido,
    )

    evento(
        db,
        solicitud,
        actor,
        "convocatoria_preparada",
        (
            "Convocatoria registrada y pendiente "
            "de envío por correo."
        ),
        visible=False,
    )

    return intervencion, notificacion


# ============================================================
# REVISIÓN PRESENCIAL
# ============================================================

@transaccion
def registrar_revision(
    db: Session,
    id_solicitud: int,
    actor: int,
    datos: RevisionPresencialRequest,
    *,
    id_intervencion: int,
):
    solicitud = obtener_para_accion(
        db,
        id_solicitud,
    )

    exigir_estado(
        solicitud,
        "en_proceso",
    )

    tipo = _tipo_solicitud(solicitud)

    intervencion = intervenciones.obtener_ultima(
        db,
        id_solicitud,
    )

    if (
        intervencion is None
        or intervencion.id_intervencion != id_intervencion
        or intervencion.estado != "convocada"
    ):
        raise SeguimientoError(
            "La convocatoria no está pendiente "
            "o fue reemplazada. Recarga la solicitud."
        )

    if intervencion.tipo != tipo:
        raise SeguimientoError(
            "La intervención no corresponde al trámite."
        )

    if (
        tipo == "firma"
        and datos.resultado != "firmada"
    ):
        raise SeguimientoError(
            "Para este trámite debe registrarse "
            "la firma.",
            400,
        )

    if (
        tipo == "conformidad"
        and datos.resultado == "firmada"
    ):
        raise SeguimientoError(
            "Para este trámite debe registrarse "
            "la conformidad.",
            400,
        )

    notificacion = notificaciones.obtener_convocatoria(
        db,
        intervencion.id_intervencion,
    )

    if (
        notificacion is None
        or notificacion.estado != "enviado"
    ):
        raise SeguimientoError(
            "La convocatoria todavía no tiene "
            "un envío de correo confirmado."
        )

    fecha_convocatoria = (
        intervencion.fecha_convocatoria.astimezone(
            ZoneInfo("America/La_Paz")
        ).date()
    )

    if datos.fecha_revision < fecha_convocatoria:
        raise SeguimientoError(
            "La fecha de revisión no puede ser "
            "anterior a la convocatoria.",
            400,
        )

    if datos.resultado in {
        "conforme",
        "firmada",
    }:
        exigir_sin_observaciones(
            db,
            id_solicitud,
        )

    intervencion = intervenciones.registrar_revision(
        db,
        intervencion,
        resultado=datos.resultado,
        fecha_revision=datos.fecha_revision,
        motivo_desacuerdo=datos.motivo_desacuerdo,
        actor=actor,
    )

    if datos.resultado == "no_conforme":
        codigo = "revision_sin_conformidad"

        detalle = (
            "El estudiante no está conforme: "
            + (datos.motivo_desacuerdo or "")
        )

    elif datos.resultado == "firmada":
        codigo = "firma_presencial_registrada"

        detalle = (
            "Se registró la firma presencial "
            "del estudiante."
        )

    else:
        codigo = "conformidad_presencial_registrada"

        detalle = (
            "Se registró la conformidad presencial "
            "del estudiante."
        )

    evento(
        db,
        solicitud,
        actor,
        codigo,
        detalle,
    )

    return intervencion


# ============================================================
# RESTRICCIÓN PARA FINALIZAR
# ============================================================

def exigir_intervencion_completada(
    db: Session,
    solicitud,
) -> None:
    tipo = solicitud.tipo_intervencion

    if tipo == "ninguna":
        return

    if tipo not in ("firma", "conformidad"):
        raise SeguimientoError(
            "La intervención configurada no es válida."
        )

    if (
        tipo == "firma"
        and _buscar_resolucion(
            db,
            solicitud.id_solicitud,
        ) is None
    ):
        raise SeguimientoError(
            "No se ha registrado la emisión "
            "de la resolución institucional."
        )

    ultima = intervenciones.obtener_ultima(
        db,
        solicitud.id_solicitud,
    )

    esperado = (
        "firmada"
        if tipo == "firma"
        else "conforme"
    )

    if (
        ultima is None
        or ultima.tipo != tipo
        or ultima.estado != esperado
    ):
        raise SeguimientoError(
            "Falta registrar la intervención "
            "presencial requerida para finalizar."
        )

    notificacion = notificaciones.obtener_convocatoria(
        db,
        ultima.id_intervencion,
    )

    if (
        notificacion is None
        or notificacion.estado != "enviado"
    ):
        raise SeguimientoError(
            "La convocatoria no tiene un envío "
            "de correo confirmado."
        )
