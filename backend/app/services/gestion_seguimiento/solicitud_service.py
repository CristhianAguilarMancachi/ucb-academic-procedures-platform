
from __future__ import annotations

from datetime import date, datetime, timezone
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.models.gestion_seguimiento.solicitud import Solicitud
from app.models.gestion_seguimiento.tramite import Tramite
from app.models.gestion_seguimiento.tramite_campo import TramiteCampo

from app.repositories.gestion_seguimiento import (
    solicitud_repository,
    tramite_repository,
    seguimiento_repository as seguimiento_repo,
)

from app.schemas.gestion_seguimiento.solicitud import (
    ListaSolicitudesResponse,
    SolicitudActualizarRequest,
    SolicitudCrearRequest,
    SolicitudResponse,
    SolicitudResumenResponse,
)

from app.services.auth.audit_service import registrar_accion_simple

from app.services.gestion_seguimiento.configuracion_flujo_service import (
    requisitos_aplicables,
    validar_flujo_envio,
)

from app.services.gestion_seguimiento.datos_pago_service import (
    obtener_documento_pago,
)


# ============================================================
# ERRORES
# ============================================================

class SolicitudServiceError(Exception):
    """Error base del servicio."""


class SolicitudNoEncontradaError(SolicitudServiceError):
    """Solicitud inexistente o ajena."""


class TramiteSolicitudNoEncontradoError(SolicitudServiceError):
    """Trámite inexistente."""


class TramiteNoDisponibleParaSolicitudError(SolicitudServiceError):
    """Trámite no habilitado."""


class SolicitudNoEsBorradorError(SolicitudServiceError):
    """La operación requiere un borrador."""


class ActualizacionSolicitudVaciaError(SolicitudServiceError):
    """No existen cambios que aplicar."""


class CampoSolicitudInvalidoError(SolicitudServiceError):
    """Campo inválido."""


class ValorCampoInvalidoError(SolicitudServiceError):
    """Valor incompatible con el campo."""


class ConfiguracionCampoInvalidaError(SolicitudServiceError):
    """Configuración inválida."""


class CamposObligatoriosFaltantesError(SolicitudServiceError):
    """Faltan datos obligatorios."""


class ConfiguracionEconomicaIncompletaError(SolicitudServiceError):
    """Configuración económica incompleta."""


class FacturaSolicitudInvalidaError(SolicitudServiceError):
    """Compatibilidad con operaciones de facturación."""


class SolicitudInconsistenteError(SolicitudServiceError):
    """Condición interna inesperada."""


# ============================================================
# PREPARACIÓN
# ============================================================

def consultar_preparacion(
    db: Session,
    id_solicitud: int,
    id_solicitante: int,
):
    from app.services.gestion_seguimiento.tramite_service import (
        obtener_tramite_catalogo_publico,
    )

    solicitud = _obtener_solicitud_del_usuario(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
        completa=True,
    )

    _validar_solicitud_borrador(solicitud)

    catalogo = obtener_tramite_catalogo_publico(
        db,
        id_tramite=solicitud.id_tramite,
    )

    campos = tramite_repository.listar_campos_tramite(
        db,
        solicitud.id_tramite,
        solo_activos=True,
    )

    requisitos = tramite_repository.listar_requisitos_tramite(
        db,
        solicitud.id_tramite,
        solo_activos=True,
    )

    aplicables = requisitos_aplicables(
        db,
        solicitud,
        requisitos,
        campos,
        solicitud.datos,
    )

    ids_aplicables = {
        requisito.id_requisito
        for requisito in aplicables
    }

    catalogo.requisitos = [
        requisito
        for requisito in catalogo.requisitos
        if requisito.id_requisito in ids_aplicables
    ]

    return catalogo


# ============================================================
# HELPERS
# ============================================================

def _obtener_solicitud_del_usuario(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitante: int,
    completa: bool = False,
    bloquear: bool = False,
) -> Solicitud:

    if bloquear:
        seguimiento_repo.bloquear_solicitud(
            db,
            id_solicitud,
        )

    solicitud = solicitud_repository.obtener_solicitud_usuario_por_id(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
        completa=completa,
    )

    if solicitud is None:
        raise SolicitudNoEncontradaError(
            "La solicitud no existe."
        )

    return solicitud


def _obtener_tramite_habilitado(
    db: Session,
    id_tramite: int,
) -> Tramite:

    tramite = tramite_repository.obtener_tramite_por_id(
        db,
        id_tramite,
    )

    if tramite is None:
        raise TramiteSolicitudNoEncontradoError(
            "El trámite indicado no existe."
        )

    if (
        not tramite.activo
        or not tramite.publicado
        or not tramite.permite_solicitudes
    ):
        raise TramiteNoDisponibleParaSolicitudError(
            "El trámite no está habilitado para recibir solicitudes."
        )

    return tramite


def _validar_solicitud_borrador(
    solicitud: Solicitud,
) -> None:

    if solicitud.estado != "borrador":
        raise SolicitudNoEsBorradorError(
            "La operación solamente está permitida "
            "mientras la solicitud sea un borrador."
        )


def _validar_valor_campo(
    campo: TramiteCampo,
    valor: Any,
) -> Any:

    tipo = campo.tipo_dato

    if tipo in {"texto", "texto_largo"}:
        if not isinstance(valor, str):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe contener texto.'
            )

        valor_limpio = valor.strip()

        if not valor_limpio:
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" no puede estar vacío.'
            )

        return valor_limpio

    if tipo == "entero":
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe contener un número entero.'
            )

        return valor

    if tipo == "decimal":
        if (
            not isinstance(valor, (int, float))
            or isinstance(valor, bool)
        ):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe contener un número.'
            )

        if isinstance(valor, float) and not isfinite(valor):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" contiene un número inválido.'
            )

        return valor

    if tipo == "fecha":
        if not isinstance(valor, str):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe contener una fecha.'
            )

        valor_limpio = valor.strip()

        try:
            fecha = date.fromisoformat(valor_limpio)
        except ValueError as exc:
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe utilizar '
                "el formato YYYY-MM-DD."
            ) from exc

        return fecha.isoformat()

    if tipo == "booleano":
        if not isinstance(valor, bool):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe ser verdadero o falso.'
            )

        return valor

    if tipo == "seleccion":
        if not isinstance(valor, str):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe contener una opción válida.'
            )

        valor_limpio = valor.strip()

        if not valor_limpio:
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" no puede estar vacío.'
            )

        configuracion = (
            campo.configuracion
            if isinstance(campo.configuracion, dict)
            else {}
        )

        opciones = configuracion.get("opciones")

        if not isinstance(opciones, list) or not opciones:
            raise ConfiguracionCampoInvalidaError(
                f'El campo "{campo.etiqueta}" no tiene '
                "opciones configuradas correctamente."
            )

        valores_permitidos: list[str] = []

        for opcion in opciones:
            if isinstance(opcion, str):
                valores_permitidos.append(opcion)
                continue

            if isinstance(opcion, dict):
                valor_opcion = opcion.get("valor")

                if isinstance(valor_opcion, str):
                    valores_permitidos.append(valor_opcion)
                    continue

            raise ConfiguracionCampoInvalidaError(
                f'El campo "{campo.etiqueta}" tiene una '
                "configuración de opciones inválida."
            )

        if valor_limpio not in valores_permitidos:
            raise ValorCampoInvalidoError(
                f'El valor indicado para "{campo.etiqueta}" '
                "no corresponde a una opción permitida."
            )

        return valor_limpio

    raise ConfiguracionCampoInvalidaError(
        f'El campo "{campo.etiqueta}" tiene '
        f'un tipo no soportado: "{tipo}".'
    )


def _normalizar_datos_borrador(
    db: Session,
    *,
    id_tramite: int,
    datos,
) -> dict[int, Any]:

    campos = tramite_repository.listar_campos_tramite(
        db,
        id_tramite,
        solo_activos=True,
    )

    campos_por_id = {
        campo.id_campo: campo
        for campo in campos
    }

    resultado: dict[int, Any] = {}

    for dato in datos:
        if dato.id_campo in resultado:
            raise CampoSolicitudInvalidoError(
                "No puede enviarse el mismo campo más de una vez."
            )

        campo = campos_por_id.get(dato.id_campo)

        if campo is None:
            raise CampoSolicitudInvalidoError(
                "Uno de los campos enviados no pertenece "
                "al trámite o ya no está activo."
            )

        resultado[dato.id_campo] = _validar_valor_campo(
            campo,
            dato.valor,
        )

    return resultado


def _obtener_perfil_minimo(
    db: Session,
    id_usuario: int,
) -> dict[str, Any] | None:

    resultado = db.execute(
        sql_text(
            """
            SELECT
                carrera_programa,
                documento_identidad
            FROM perfil_academico
            WHERE id_usuario = :id_usuario
            """
        ),
        {"id_usuario": id_usuario},
    ).mappings().one_or_none()

    return dict(resultado) if resultado is not None else None


def _completar_estado_requisitos_respuesta(
    db: Session,
    solicitud: Solicitud,
    respuesta: SolicitudResponse,
) -> SolicitudResponse:

    respuesta.documento_identidad_pago = obtener_documento_pago(
        db,
        solicitud,
    )

    declarados = {
        historial.id_solicitud_requisito
        for historial in seguimiento_repo.listar_historial(
            db,
            solicitud.id_solicitud,
        )
        if historial.evento == "entrega_fisica_declarada"
    }

    solicitud_activa = solicitud.estado in {
        "pendiente_recepcion",
        "en_revision",
        "en_proceso",
    }

    for requisito in respuesta.requisitos:
        requisito.entrega_declarada = (
            requisito.id_solicitud_requisito in declarados
        )

        requisito.puede_declarar_entrega = bool(
            requisito.requiere_presentacion_fisica
            and not requisito.presentado
            and not requisito.entrega_declarada
            and solicitud_activa
        )

        requisito.puede_registrar_factura = bool(
            requisito.es_economico
            and requisito.estado_verificacion != "cumple"
            and solicitud_activa
        )

    return respuesta


def _obtener_respuesta_completa(
    db: Session,
    id_solicitud: int,
) -> SolicitudResponse:

    solicitud = solicitud_repository.obtener_solicitud_por_id_completa(
        db,
        id_solicitud,
    )

    if solicitud is None:
        raise SolicitudNoEncontradaError(
            "La solicitud no existe."
        )

    respuesta = SolicitudResponse.model_validate(solicitud)

    return _completar_estado_requisitos_respuesta(
        db,
        solicitud,
        respuesta,
    )


# ============================================================
# CREACIÓN DE BORRADOR
# ============================================================

def crear_solicitud(
    db: Session,
    *,
    id_solicitante: int,
    datos: SolicitudCrearRequest,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SolicitudResponse:

    _obtener_tramite_habilitado(
        db,
        datos.id_tramite,
    )

    try:
        solicitud = solicitud_repository.crear_solicitud(
            db,
            id_solicitante=id_solicitante,
            id_tramite=datos.id_tramite,
        )

        registrar_accion_simple(
            db,
            accion="crear_solicitud_borrador",
            modulo="gestion_seguimiento",
            id_usuario_actor=id_solicitante,
            entidad="solicitud",
            id_entidad=str(solicitud.id_solicitud),
            exitoso=True,
            detalle={
                "id_tramite": datos.id_tramite,
                "estado": "borrador",
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        seguimiento_repo.registrar_historial(
            db,
            solicitud.id_solicitud,
            id_solicitante,
            "solicitud_creada",
            "Solicitud creada en borrador.",
        )

        id_solicitud = solicitud.id_solicitud

        db.commit()

        return _obtener_respuesta_completa(
            db,
            id_solicitud,
        )

    except Exception:
        db.rollback()
        raise


# ============================================================
# CONSULTAS
# ============================================================

def obtener_solicitud(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitante: int,
) -> SolicitudResponse:

    solicitud = _obtener_solicitud_del_usuario(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
        completa=True,
    )

    respuesta = SolicitudResponse.model_validate(solicitud)

    return _completar_estado_requisitos_respuesta(
        db,
        solicitud,
        respuesta,
    )


def listar_mis_solicitudes(
    db: Session,
    *,
    id_solicitante: int,
    estado: str | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> ListaSolicitudesResponse:

    solicitudes, total = solicitud_repository.listar_solicitudes_usuario(
        db,
        id_solicitante=id_solicitante,
        estado=estado,
        pagina=pagina,
        por_pagina=por_pagina,
    )

    return ListaSolicitudesResponse(
        items=[
            SolicitudResumenResponse.model_validate(solicitud)
            for solicitud in solicitudes
        ],
        total=total,
        pagina=max(pagina, 1),
        por_pagina=min(max(por_pagina, 1), 100),
    )


# ============================================================
# ACTUALIZAR BORRADOR
# ============================================================

def actualizar_solicitud(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitante: int,
    datos: SolicitudActualizarRequest,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SolicitudResponse:

    solicitud = _obtener_solicitud_del_usuario(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
        bloquear=True,
    )

    _validar_solicitud_borrador(solicitud)

    campos_recibidos = datos.model_fields_set

    actualizar_datos = (
        "datos" in campos_recibidos
        and datos.datos is not None
    )

    campos_contacto = {
        "nombre_contacto",
        "telefono_contacto",
        "correo_contacto",
    }

    contacto_recibido = campos_contacto & campos_recibidos

    if not actualizar_datos and not contacto_recibido:
        raise ActualizacionSolicitudVaciaError(
            "Debe proporcionar información "
            "para actualizar el borrador."
        )

    valores_normalizados: dict[int, Any] = {}

    if actualizar_datos:
        valores_normalizados = _normalizar_datos_borrador(
            db,
            id_tramite=solicitud.id_tramite,
            datos=datos.datos,
        )

    try:
        if actualizar_datos:
            datos_actuales = solicitud_repository.listar_datos_solicitud(
                db,
                solicitud.id_solicitud,
            )

            ids_recibidos = set(valores_normalizados.keys())

            for dato_actual in datos_actuales:
                if dato_actual.id_campo not in ids_recibidos:
                    solicitud_repository.eliminar_dato_solicitud(
                        db,
                        dato_actual,
                    )

            for id_campo, valor in valores_normalizados.items():
                solicitud_repository.guardar_dato_solicitud(
                    db,
                    id_solicitud=solicitud.id_solicitud,
                    id_campo=id_campo,
                    valor=valor,
                )

        if "nombre_contacto" in campos_recibidos:
            solicitud.nombre_contacto = datos.nombre_contacto

        if "telefono_contacto" in campos_recibidos:
            solicitud.telefono_contacto = datos.telefono_contacto

        if "correo_contacto" in campos_recibidos:
            solicitud.correo_contacto = (
                str(datos.correo_contacto)
                if datos.correo_contacto is not None
                else None
            )

        db.flush()

        registrar_accion_simple(
            db,
            accion="actualizar_solicitud_borrador",
            modulo="gestion_seguimiento",
            id_usuario_actor=id_solicitante,
            entidad="solicitud",
            id_entidad=str(solicitud.id_solicitud),
            exitoso=True,
            detalle={
                "campos_guardados": sorted(
                    valores_normalizados.keys()
                ),
                "contacto_actualizado": sorted(
                    contacto_recibido
                ),
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        return _obtener_respuesta_completa(
            db,
            solicitud.id_solicitud,
        )

    except Exception:
        db.rollback()
        raise


# ============================================================
# ELIMINAR BORRADOR
# ============================================================

def eliminar_solicitud(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitante: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> None:

    solicitud = _obtener_solicitud_del_usuario(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
        bloquear=True,
    )

    _validar_solicitud_borrador(solicitud)

    id_tramite = solicitud.id_tramite

    try:
        solicitud_repository.eliminar_solicitud(
            db,
            solicitud,
        )

        registrar_accion_simple(
            db,
            accion="eliminar_solicitud_borrador",
            modulo="gestion_seguimiento",
            id_usuario_actor=id_solicitante,
            entidad="solicitud",
            id_entidad=str(id_solicitud),
            exitoso=True,
            detalle={
                "id_tramite": id_tramite,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise


# ============================================================
# ENVÍO FORMAL
# ============================================================

def enviar_solicitud(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitante: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SolicitudResponse:

    solicitud = _obtener_solicitud_del_usuario(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
        bloquear=True,
    )

    _validar_solicitud_borrador(solicitud)

    tramite = _obtener_tramite_habilitado(
        db,
        solicitud.id_tramite,
    )

    # --------------------------------------------------------
    # DATOS BÁSICOS OBLIGATORIOS
    # --------------------------------------------------------

    faltantes_basicos: list[str] = []

    if not (
        solicitud.nombre_contacto
        and solicitud.nombre_contacto.strip()
    ):
        faltantes_basicos.append("Nombre de contacto")

    if not (
        solicitud.telefono_contacto
        and solicitud.telefono_contacto.strip()
    ):
        faltantes_basicos.append("Teléfono de contacto")

    if not (
        solicitud.correo_contacto
        and solicitud.correo_contacto.strip()
    ):
        faltantes_basicos.append("Correo de contacto")

    perfil = _obtener_perfil_minimo(
        db,
        id_solicitante,
    )

    if not (
        perfil
        and perfil.get("carrera_programa")
        and str(perfil["carrera_programa"]).strip()
    ):
        faltantes_basicos.append("Carrera o programa")

    if not (
        perfil
        and perfil.get("documento_identidad")
        and str(perfil["documento_identidad"]).strip()
    ):
        faltantes_basicos.append("Documento de identidad (CI)")

    if faltantes_basicos:
        raise CamposObligatoriosFaltantesError(
            "Completa los datos obligatorios antes "
            "de enviar la solicitud: "
            + ", ".join(faltantes_basicos)
            + "."
        )

    # --------------------------------------------------------
    # CAMPOS DINÁMICOS
    # --------------------------------------------------------

    campos = tramite_repository.listar_campos_tramite(
        db,
        solicitud.id_tramite,
        solo_activos=True,
    )

    datos_guardados = solicitud_repository.listar_datos_solicitud(
        db,
        solicitud.id_solicitud,
    )

    datos_por_campo = {
        dato.id_campo: dato
        for dato in datos_guardados
    }

    ids_campos_actuales = {
        campo.id_campo
        for campo in campos
    }

    if set(datos_por_campo) - ids_campos_actuales:
        raise ValorCampoInvalidoError(
            "El formulario cambió. Guarda nuevamente "
            "el borrador con sus campos actuales antes de enviar."
        )

    faltantes: list[str] = []

    for campo in campos:
        dato = datos_por_campo.get(campo.id_campo)

        if dato is None:
            if campo.obligatorio:
                faltantes.append(campo.etiqueta)
            continue

        _validar_valor_campo(
            campo,
            dato.valor,
        )

    if faltantes:
        raise CamposObligatoriosFaltantesError(
            "Faltan campos obligatorios: "
            + ", ".join(faltantes)
            + "."
        )

    # --------------------------------------------------------
    # VALIDACIÓN DE SNAPSHOT
    # --------------------------------------------------------

    requisitos_generados = (
        solicitud_repository.contar_requisitos_solicitud(
            db,
            solicitud.id_solicitud,
        )
    )

    if requisitos_generados > 0:
        raise SolicitudInconsistenteError(
            "El borrador ya contiene una fotografía "
            "de requisitos y no puede enviarse nuevamente."
        )

    # --------------------------------------------------------
    # REQUISITOS Y MODALIDAD
    # --------------------------------------------------------

    validar_flujo_envio(
        db,
        tramite,
    )

    requisitos = tramite_repository.listar_requisitos_tramite(
        db,
        solicitud.id_tramite,
        solo_activos=True,
    )

    requisitos = requisitos_aplicables(
        db,
        solicitud,
        requisitos,
        campos,
        datos_guardados,
    )

    gestion_actual = datetime.now(
        ZoneInfo("America/La_Paz")
    ).year

    fecha_envio = datetime.now(timezone.utc)

    try:
        # ----------------------------------------------------
        # SNAPSHOT DE CONFIGURACIÓN
        # ----------------------------------------------------

        solicitud.nombre_tramite_snapshot = tramite.nombre
        solicitud.tipo_finalizacion = tramite.tipo_finalizacion
        solicitud.tipo_intervencion = tramite.tipo_intervencion

        for campo in campos:
            dato = datos_por_campo.get(campo.id_campo)

            if dato is None:
                continue

            dato.clave_snapshot = campo.clave
            dato.etiqueta_snapshot = campo.etiqueta

        # ----------------------------------------------------
        # SNAPSHOT DE REQUISITOS
        # ----------------------------------------------------

        for requisito in requisitos:
            es_economico = bool(
                requisito.configuraciones_economicas
            )

            configuracion_actual = None

            if es_economico:
                configuracion_actual = (
                    tramite_repository
                    .obtener_configuracion_economica_por_gestion(
                        db,
                        id_requisito=requisito.id_requisito,
                        gestion=gestion_actual,
                    )
                )

                if (
                    configuracion_actual is None
                    or not configuracion_actual.activo
                ):
                    raise ConfiguracionEconomicaIncompletaError(
                        f'El requisito "{requisito.nombre}" '
                        "no tiene configuración económica activa "
                        f"para la gestión {gestion_actual}."
                    )

                codigo_externo = (
                    configuracion_actual.codigo_concepto_externo
                )

                if (
                    codigo_externo is None
                    or not codigo_externo.strip()
                ):
                    raise ConfiguracionEconomicaIncompletaError(
                        f'El requisito "{requisito.nombre}" '
                        "no tiene código de concepto externo configurado."
                    )

            copia = solicitud_repository.crear_requisito_solicitud(
                db,
                id_solicitud=solicitud.id_solicitud,
                id_requisito_origen=requisito.id_requisito,
                nombre=requisito.nombre,
                descripcion=requisito.descripcion,
                obligatorio=requisito.obligatorio,
                orden=requisito.orden,
                id_requisito_economico_origen=(
                    configuracion_actual.id_requisito_economico
                    if configuracion_actual is not None
                    else None
                ),
                concepto_economico=(
                    configuracion_actual.concepto
                    if configuracion_actual is not None
                    else None
                ),
                monto_economico=(
                    configuracion_actual.monto
                    if configuracion_actual is not None
                    else None
                ),
                moneda=(
                    configuracion_actual.moneda
                    if configuracion_actual is not None
                    else None
                ),
                gestion=(
                    configuracion_actual.gestion
                    if configuracion_actual is not None
                    else None
                ),
                codigo_concepto_externo=(
                    configuracion_actual.codigo_concepto_externo
                    if configuracion_actual is not None
                    else None
                ),
                numero_factura=None,
            )

            copia.requiere_presentacion_fisica = (
                requisito.requiere_presentacion_fisica
            )

            copia.condicion_snapshot = requisito.condicion

        # ----------------------------------------------------
        # ENVIAR SOLICITUD
        # ----------------------------------------------------

        solicitud_repository.marcar_solicitud_enviada(
            db,
            solicitud,
            fecha_envio=fecha_envio,
        )

        registrar_accion_simple(
            db,
            accion="enviar_solicitud",
            modulo="gestion_seguimiento",
            id_usuario_actor=id_solicitante,
            entidad="solicitud",
            id_entidad=str(solicitud.id_solicitud),
            exitoso=True,
            detalle={
                "id_tramite": solicitud.id_tramite,
                "estado": "pendiente_recepcion",
                "gestion": gestion_actual,
                "cantidad_requisitos": len(requisitos),
                "tipo_intervencion": solicitud.tipo_intervencion,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        seguimiento_repo.registrar_historial(
            db,
            id_solicitud,
            id_solicitante,
            "solicitud_enviada",
            "Solicitud registrada y enviada para atención.",
        )

        db.commit()

        return _obtener_respuesta_completa(
            db,
            solicitud.id_solicitud,
        )

    except Exception:
        db.rollback()
        raise
