from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento.tramite_repository import (
    actualizar_campo,
    actualizar_configuracion_economica,
    actualizar_etapa,
    actualizar_requisito,
    actualizar_tramite,
    crear_campo,
    crear_configuracion_economica,
    crear_etapa,
    crear_requisito,
    crear_tramite,
    listar_catalogo_publicado,
    listar_tramites,
    obtener_campo_por_clave,
    obtener_campo_por_id,
    obtener_configuracion_economica_por_gestion,
    obtener_configuracion_economica_por_id,
    obtener_etapa_final,
    obtener_etapa_inicial,
    obtener_etapa_por_id,
    obtener_etapa_por_orden,
    obtener_requisito_por_id,
    obtener_requisito_por_nombre,
    obtener_tramite_por_id,
    obtener_tramite_por_id_completo,
    obtener_tramite_por_nombre,
)
from app.repositories.gestion_seguimiento.unidad_repository import (
    obtener_unidad_por_id,
)
from app.schemas.gestion_seguimiento.tramite import (
    ListaCatalogoTramitesResponse,
    ListaTramitesResponse,
    TramiteActualizarRequest,
    TramiteCatalogoCampoResponse,
    TramiteCatalogoDetalleResponse,
    TramiteCatalogoEconomicoResponse,
    TramiteCatalogoRequisitoResponse,
    TramiteCrearRequest,
    TramiteDetalleResponse,
    TramiteResponse,
    TramiteResumenResponse,
)
from app.schemas.gestion_seguimiento.tramite_campo import (
    TramiteCampoActualizarRequest,
    TramiteCampoCrearRequest,
    TramiteCampoResponse,
)
from app.schemas.gestion_seguimiento.tramite_etapa import (
    TramiteEtapaActualizarRequest,
    TramiteEtapaCrearRequest,
    TramiteEtapaResponse,
)
from app.schemas.gestion_seguimiento.tramite_requisito import (
    RequisitoEconomicoActualizarRequest,
    RequisitoEconomicoCrearRequest,
    RequisitoEconomicoResponse,
    TramiteRequisitoActualizarRequest,
    TramiteRequisitoCrearRequest,
    TramiteRequisitoResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)


# ============================================================
# EXCEPCIONES
# ============================================================


class TramiteServiceError(Exception):
    """
    Error base del catálogo de trámites.
    """


class TramiteNoEncontradoError(TramiteServiceError):
    pass


class TramiteDuplicadoError(TramiteServiceError):
    pass


class ActualizacionTramiteVaciaError(TramiteServiceError):
    pass


class ConfiguracionTramiteInvalidaError(TramiteServiceError):
    pass


class RequisitoNoEncontradoError(TramiteServiceError):
    pass


class RequisitoDuplicadoError(TramiteServiceError):
    pass


class RequisitoNoPerteneceTramiteError(TramiteServiceError):
    pass


class ConfiguracionEconomicaNoEncontradaError(
    TramiteServiceError
):
    pass


class ConfiguracionEconomicaDuplicadaError(
    TramiteServiceError
):
    pass


class CampoNoEncontradoError(TramiteServiceError):
    pass


class CampoDuplicadoError(TramiteServiceError):
    pass


class CampoNoPerteneceTramiteError(TramiteServiceError):
    pass


class EtapaNoEncontradaError(TramiteServiceError):
    pass


class EtapaNoPerteneceTramiteError(TramiteServiceError):
    pass


class EtapaDuplicadaError(TramiteServiceError):
    pass


class UnidadNoEncontradaError(TramiteServiceError):
    pass


class UnidadInactivaError(TramiteServiceError):
    pass


# ============================================================
# FUNCIONES INTERNAS
# ============================================================


def _validar_estado_tramite(
    *,
    activo: bool,
    publicado: bool,
    permite_solicitudes: bool,
) -> None:
    """
    Garantiza coherencia básica entre los estados del catálogo.
    """
    if publicado and not activo:
        raise ConfiguracionTramiteInvalidaError(
            "Un trámite inactivo no puede permanecer publicado."
        )

    if permite_solicitudes and not activo:
        raise ConfiguracionTramiteInvalidaError(
            "Un trámite inactivo no puede permitir solicitudes."
        )

    if permite_solicitudes and not publicado:
        raise ConfiguracionTramiteInvalidaError(
            "Un trámite debe estar publicado antes de permitir "
            "solicitudes."
        )


def _obtener_tramite_o_error(
    db: Session,
    id_tramite: int,
):
    tramite = obtener_tramite_por_id(
        db,
        id_tramite,
    )

    if tramite is None:
        raise TramiteNoEncontradoError(
            "El trámite indicado no existe."
        )

    return tramite


def _obtener_requisito_del_tramite(
    db: Session,
    *,
    id_tramite: int,
    id_requisito: int,
):
    requisito = obtener_requisito_por_id(
        db,
        id_requisito,
    )

    if requisito is None:
        raise RequisitoNoEncontradoError(
            "El requisito indicado no existe."
        )

    if requisito.id_tramite != id_tramite:
        raise RequisitoNoPerteneceTramiteError(
            "El requisito no pertenece al trámite indicado."
        )

    return requisito


def _obtener_campo_del_tramite(
    db: Session,
    *,
    id_tramite: int,
    id_campo: int,
):
    campo = obtener_campo_por_id(
        db,
        id_campo,
    )

    if campo is None:
        raise CampoNoEncontradoError(
            "El campo indicado no existe."
        )

    if campo.id_tramite != id_tramite:
        raise CampoNoPerteneceTramiteError(
            "El campo no pertenece al trámite indicado."
        )

    return campo


def _obtener_etapa_del_tramite(
    db: Session,
    *,
    id_tramite: int,
    id_etapa: int,
):
    etapa = obtener_etapa_por_id(
        db,
        id_etapa,
    )

    if etapa is None:
        raise EtapaNoEncontradaError(
            "La etapa indicada no existe."
        )

    if etapa.id_tramite != id_tramite:
        raise EtapaNoPerteneceTramiteError(
            "La etapa no pertenece al trámite indicado."
        )

    return etapa


def _validar_unidad_etapa(
    db: Session,
    id_unidad: int | None,
) -> None:
    """
    Valida una unidad únicamente cuando la etapa ya tiene
    una unidad institucional confirmada.
    """
    if id_unidad is None:
        return

    unidad = obtener_unidad_por_id(
        db,
        id_unidad,
    )

    if unidad is None:
        raise UnidadNoEncontradaError(
            "La unidad administrativa indicada no existe."
        )

    if not unidad.activo:
        raise UnidadInactivaError(
            "No puede asociarse una etapa a una unidad inactiva."
        )


# ============================================================
# TRÁMITES
# ============================================================


def crear_tramite_catalogo(
    db: Session,
    *,
    datos: TramiteCrearRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TramiteResponse:
    """
    Registra un trámite en el catálogo.
    """
    existente = obtener_tramite_por_nombre(
        db,
        datos.nombre,
    )

    if existente is not None:
        raise TramiteDuplicadoError(
            "Ya existe un trámite con ese nombre."
        )

    _validar_estado_tramite(
        activo=datos.activo,
        publicado=datos.publicado,
        permite_solicitudes=datos.permite_solicitudes,
    )

    try:
        tramite = crear_tramite(
            db,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            activo=datos.activo,
            publicado=datos.publicado,
            permite_solicitudes=datos.permite_solicitudes,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="crear_tramite",
            modulo="gestion_seguimiento",
            entidad="tramite",
            id_entidad=tramite.id_tramite,
            detalle={
                "nombre": tramite.nombre,
                "activo": tramite.activo,
                "publicado": tramite.publicado,
                "permite_solicitudes": (
                    tramite.permite_solicitudes
                ),
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(tramite)

        return TramiteResponse.model_validate(
            tramite
        )

    except IntegrityError as exc:
        db.rollback()

        raise TramiteDuplicadoError(
            "No fue posible crear el trámite porque existe "
            "un registro incompatible."
        ) from exc

    except Exception:
        db.rollback()
        raise


def listar_tramites_administracion(
    db: Session,
    *,
    pagina: int = 1,
    por_pagina: int = 20,
    activo: bool | None = None,
    publicado: bool | None = None,
    permite_solicitudes: bool | None = None,
    texto_busqueda: str | None = None,
) -> ListaTramitesResponse:
    """
    Lista el catálogo administrativo con filtros.
    """
    tramites, total = listar_tramites(
        db,
        pagina=pagina,
        por_pagina=por_pagina,
        activo=activo,
        publicado=publicado,
        permite_solicitudes=permite_solicitudes,
        texto_busqueda=texto_busqueda,
    )

    return ListaTramitesResponse(
        items=[
            TramiteResponse.model_validate(tramite)
            for tramite in tramites
        ],
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


def obtener_tramite_administracion(
    db: Session,
    *,
    id_tramite: int,
) -> TramiteDetalleResponse:
    """
    Obtiene toda la configuración administrativa de un trámite.
    """
    tramite = obtener_tramite_por_id_completo(
        db,
        id_tramite,
    )

    if tramite is None:
        raise TramiteNoEncontradoError(
            "El trámite indicado no existe."
        )

    return TramiteDetalleResponse.model_validate(
        tramite
    )


def actualizar_tramite_catalogo(
    db: Session,
    *,
    id_tramite: int,
    datos: TramiteActualizarRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TramiteResponse:
    """
    Modifica la configuración general de un trámite.
    """
    if not datos.model_fields_set:
        raise ActualizacionTramiteVaciaError(
            "Debe indicarse al menos un dato para actualizar."
        )

    tramite = _obtener_tramite_o_error(
        db,
        id_tramite,
    )

    if (
        "nombre" in datos.model_fields_set
        and datos.nombre is not None
        and datos.nombre.lower() != tramite.nombre.lower()
    ):
        existente = obtener_tramite_por_nombre(
            db,
            datos.nombre,
        )

        if (
            existente is not None
            and existente.id_tramite != tramite.id_tramite
        ):
            raise TramiteDuplicadoError(
                "Ya existe un trámite con ese nombre."
            )

    activo_final = (
        datos.activo
        if "activo" in datos.model_fields_set
        and datos.activo is not None
        else tramite.activo
    )

    publicado_final = (
        datos.publicado
        if "publicado" in datos.model_fields_set
        and datos.publicado is not None
        else tramite.publicado
    )

    permite_final = (
        datos.permite_solicitudes
        if (
            "permite_solicitudes"
            in datos.model_fields_set
            and datos.permite_solicitudes is not None
        )
        else tramite.permite_solicitudes
    )

    _validar_estado_tramite(
        activo=activo_final,
        publicado=publicado_final,
        permite_solicitudes=permite_final,
    )

    detalle_anterior = {
        "nombre": tramite.nombre,
        "descripcion": tramite.descripcion,
        "activo": tramite.activo,
        "publicado": tramite.publicado,
        "permite_solicitudes": tramite.permite_solicitudes,
    }

    try:
        actualizar_tramite(
            db,
            tramite,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            activo=datos.activo,
            publicado=datos.publicado,
            permite_solicitudes=datos.permite_solicitudes,
            actualizar_descripcion=(
                "descripcion" in datos.model_fields_set
            ),
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="actualizar_tramite",
            modulo="gestion_seguimiento",
            entidad="tramite",
            id_entidad=tramite.id_tramite,
            detalle={
                "antes": detalle_anterior,
                "despues": {
                    "nombre": tramite.nombre,
                    "descripcion": tramite.descripcion,
                    "activo": tramite.activo,
                    "publicado": tramite.publicado,
                    "permite_solicitudes": (
                        tramite.permite_solicitudes
                    ),
                },
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(tramite)

        return TramiteResponse.model_validate(
            tramite
        )

    except IntegrityError as exc:
        db.rollback()

        raise TramiteDuplicadoError(
            "No fue posible actualizar el trámite."
        ) from exc

    except Exception:
        db.rollback()
        raise


def obtener_catalogo_publicado(
    db: Session,
) -> ListaCatalogoTramitesResponse:
    """
    Devuelve los trámites activos y publicados visibles
    para consulta.
    """
    tramites = listar_catalogo_publicado(
        db
    )

    items = [
        TramiteResumenResponse.model_validate(
            tramite
        )
        for tramite in tramites
    ]

    return ListaCatalogoTramitesResponse(
        items=items,
        total=len(items),
    )


def obtener_tramite_catalogo_publico(
    db: Session,
    *,
    id_tramite: int,
) -> TramiteCatalogoDetalleResponse:
    """
    Devuelve el detalle visible de un trámite publicado.

    Solo expone:
    - información general;
    - requisitos activos;
    - información económica vigente;
    - campos configurables activos.

    No expone etapas ni unidades administrativas.
    """
    tramite = obtener_tramite_por_id_completo(
        db,
        id_tramite,
    )

    if (
        tramite is None
        or not tramite.activo
        or not tramite.publicado
    ):
        raise TramiteNoEncontradoError(
            "El trámite indicado no está disponible "
            "en el catálogo."
        )

    gestion_actual = datetime.now(
        ZoneInfo("America/La_Paz")
    ).year

    requisitos_visibles = []

    requisitos_activos = sorted(
        (
            requisito
            for requisito in tramite.requisitos
            if requisito.activo
        ),
        key=lambda requisito: (
            requisito.orden,
            requisito.id_requisito,
        ),
    )

    for requisito in requisitos_activos:
        tiene_configuracion_economica = bool(
            requisito.configuraciones_economicas
        )

        informacion_economica = None

        if tiene_configuracion_economica:
            configuracion_actual = next(
                (
                    configuracion
                    for configuracion
                    in requisito.configuraciones_economicas
                    if (
                        configuracion.activo
                        and configuracion.gestion
                        == gestion_actual
                    )
                ),
                None,
            )

            if configuracion_actual is not None:
                informacion_economica = (
                    TramiteCatalogoEconomicoResponse(
                        concepto=(
                            configuracion_actual.concepto
                        ),
                        monto=(
                            configuracion_actual.monto
                        ),
                        moneda=(
                            configuracion_actual.moneda
                        ),
                        gestion=(
                            configuracion_actual.gestion
                        ),
                    )
                )

        requisitos_visibles.append(
            TramiteCatalogoRequisitoResponse(
                id_requisito=requisito.id_requisito,
                nombre=requisito.nombre,
                descripcion=requisito.descripcion,
                obligatorio=requisito.obligatorio,
                orden=requisito.orden,
                es_economico=(
                    tiene_configuracion_economica
                ),
                informacion_economica=(
                    informacion_economica
                ),
            )
        )

    campos_visibles = [
        TramiteCatalogoCampoResponse(
            id_campo=campo.id_campo,
            clave=campo.clave,
            etiqueta=campo.etiqueta,
            descripcion=campo.descripcion,
            tipo_dato=campo.tipo_dato,
            obligatorio=campo.obligatorio,
            orden=campo.orden,
            configuracion=campo.configuracion,
        )
        for campo in sorted(
            (
                campo
                for campo in tramite.campos
                if campo.activo
            ),
            key=lambda campo: (
                campo.orden,
                campo.id_campo,
            ),
        )
    ]

    return TramiteCatalogoDetalleResponse(
        id_tramite=tramite.id_tramite,
        nombre=tramite.nombre,
        descripcion=tramite.descripcion,
        permite_solicitudes=(
            tramite.permite_solicitudes
        ),
        requisitos=requisitos_visibles,
        campos=campos_visibles,
    )


# ============================================================
# REQUISITOS
# ============================================================


def agregar_requisito_tramite(
    db: Session,
    *,
    id_tramite: int,
    datos: TramiteRequisitoCrearRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TramiteRequisitoResponse:
    """
    Agrega un requisito confirmado a un trámite.
    """
    _obtener_tramite_o_error(
        db,
        id_tramite,
    )

    existente = obtener_requisito_por_nombre(
        db,
        id_tramite=id_tramite,
        nombre=datos.nombre,
    )

    if existente is not None:
        raise RequisitoDuplicadoError(
            "Ya existe un requisito con ese nombre "
            "para el trámite."
        )

    try:
        requisito = crear_requisito(
            db,
            id_tramite=id_tramite,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            obligatorio=datos.obligatorio,
            orden=datos.orden,
            activo=datos.activo,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="crear_requisito_tramite",
            modulo="gestion_seguimiento",
            entidad="tramite_requisito",
            id_entidad=requisito.id_requisito,
            detalle={
                "id_tramite": id_tramite,
                "nombre": requisito.nombre,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        requisito = obtener_requisito_por_id(
            db,
            requisito.id_requisito,
        )

        return TramiteRequisitoResponse.model_validate(
            requisito
        )

    except IntegrityError as exc:
        db.rollback()

        raise RequisitoDuplicadoError(
            "No fue posible registrar el requisito."
        ) from exc

    except Exception:
        db.rollback()
        raise


def actualizar_requisito_tramite(
    db: Session,
    *,
    id_tramite: int,
    id_requisito: int,
    datos: TramiteRequisitoActualizarRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TramiteRequisitoResponse:
    """
    Modifica un requisito existente.
    """
    if not datos.model_fields_set:
        raise TramiteServiceError(
            "Debe indicarse al menos un dato para actualizar."
        )

    requisito = _obtener_requisito_del_tramite(
        db,
        id_tramite=id_tramite,
        id_requisito=id_requisito,
    )

    if (
        "nombre" in datos.model_fields_set
        and datos.nombre is not None
        and datos.nombre.lower() != requisito.nombre.lower()
    ):
        existente = obtener_requisito_por_nombre(
            db,
            id_tramite=id_tramite,
            nombre=datos.nombre,
        )

        if (
            existente is not None
            and existente.id_requisito != id_requisito
        ):
            raise RequisitoDuplicadoError(
                "Ya existe un requisito con ese nombre."
            )

    try:
        actualizar_requisito(
            db,
            requisito,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            obligatorio=datos.obligatorio,
            orden=datos.orden,
            activo=datos.activo,
            actualizar_descripcion=(
                "descripcion" in datos.model_fields_set
            ),
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="actualizar_requisito_tramite",
            modulo="gestion_seguimiento",
            entidad="tramite_requisito",
            id_entidad=id_requisito,
            detalle={
                "id_tramite": id_tramite,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        requisito = obtener_requisito_por_id(
            db,
            id_requisito,
        )

        return TramiteRequisitoResponse.model_validate(
            requisito
        )

    except IntegrityError as exc:
        db.rollback()

        raise RequisitoDuplicadoError(
            "No fue posible actualizar el requisito."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ============================================================
# INFORMACIÓN ECONÓMICA
# ============================================================


def agregar_configuracion_economica(
    db: Session,
    *,
    id_tramite: int,
    id_requisito: int,
    datos: RequisitoEconomicoCrearRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> RequisitoEconomicoResponse:
    """
    Agrega la configuración económica conocida para una gestión.
    """
    _obtener_requisito_del_tramite(
        db,
        id_tramite=id_tramite,
        id_requisito=id_requisito,
    )

    existente = obtener_configuracion_economica_por_gestion(
        db,
        id_requisito=id_requisito,
        gestion=datos.gestion,
    )

    if existente is not None:
        raise ConfiguracionEconomicaDuplicadaError(
            "El requisito ya tiene una configuración económica "
            "para esa gestión."
        )

    try:
        configuracion = crear_configuracion_economica(
            db,
            id_requisito=id_requisito,
            concepto=datos.concepto,
            monto=datos.monto,
            moneda=datos.moneda,
            gestion=datos.gestion,
            codigo_concepto_externo=(
                datos.codigo_concepto_externo
            ),
            activo=datos.activo,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="crear_configuracion_economica",
            modulo="gestion_seguimiento",
            entidad="tramite_requisito_economico",
            id_entidad=configuracion.id_requisito_economico,
            detalle={
                "id_tramite": id_tramite,
                "id_requisito": id_requisito,
                "gestion": datos.gestion,
                "monto": str(datos.monto),
                "moneda": datos.moneda,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(configuracion)

        return RequisitoEconomicoResponse.model_validate(
            configuracion
        )

    except IntegrityError as exc:
        db.rollback()

        raise ConfiguracionEconomicaDuplicadaError(
            "No fue posible guardar la configuración económica."
        ) from exc

    except Exception:
        db.rollback()
        raise


def actualizar_configuracion_economica_tramite(
    db: Session,
    *,
    id_tramite: int,
    id_requisito: int,
    id_requisito_economico: int,
    datos: RequisitoEconomicoActualizarRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> RequisitoEconomicoResponse:
    """
    Actualiza una configuración económica existente.
    """
    if not datos.model_fields_set:
        raise TramiteServiceError(
            "Debe indicarse al menos un dato para actualizar."
        )

    _obtener_requisito_del_tramite(
        db,
        id_tramite=id_tramite,
        id_requisito=id_requisito,
    )

    configuracion = obtener_configuracion_economica_por_id(
        db,
        id_requisito_economico,
    )

    if (
        configuracion is None
        or configuracion.id_requisito != id_requisito
    ):
        raise ConfiguracionEconomicaNoEncontradaError(
            "La configuración económica indicada no existe "
            "para este requisito."
        )

    if (
        "gestion" in datos.model_fields_set
        and datos.gestion is not None
        and datos.gestion != configuracion.gestion
    ):
        existente = obtener_configuracion_economica_por_gestion(
            db,
            id_requisito=id_requisito,
            gestion=datos.gestion,
        )

        if (
            existente is not None
            and existente.id_requisito_economico
            != id_requisito_economico
        ):
            raise ConfiguracionEconomicaDuplicadaError(
                "Ya existe una configuración económica "
                "para esa gestión."
            )

    try:
        actualizar_configuracion_economica(
            db,
            configuracion,
            concepto=datos.concepto,
            monto=datos.monto,
            moneda=datos.moneda,
            gestion=datos.gestion,
            codigo_concepto_externo=(
                datos.codigo_concepto_externo
            ),
            activo=datos.activo,
            actualizar_codigo_externo=(
                "codigo_concepto_externo"
                in datos.model_fields_set
            ),
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="actualizar_configuracion_economica",
            modulo="gestion_seguimiento",
            entidad="tramite_requisito_economico",
            id_entidad=id_requisito_economico,
            detalle={
                "id_tramite": id_tramite,
                "id_requisito": id_requisito,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(configuracion)

        return RequisitoEconomicoResponse.model_validate(
            configuracion
        )

    except IntegrityError as exc:
        db.rollback()

        raise ConfiguracionEconomicaDuplicadaError(
            "No fue posible actualizar la configuración económica."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ============================================================
# CAMPOS CONFIGURABLES
# ============================================================


def agregar_campo_tramite(
    db: Session,
    *,
    id_tramite: int,
    datos: TramiteCampoCrearRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TramiteCampoResponse:
    """
    Agrega un campo configurable a un trámite.
    """
    _obtener_tramite_o_error(
        db,
        id_tramite,
    )

    existente = obtener_campo_por_clave(
        db,
        id_tramite=id_tramite,
        clave=datos.clave,
    )

    if existente is not None:
        raise CampoDuplicadoError(
            "Ya existe un campo con esa clave para el trámite."
        )

    try:
        campo = crear_campo(
            db,
            id_tramite=id_tramite,
            clave=datos.clave,
            etiqueta=datos.etiqueta,
            descripcion=datos.descripcion,
            tipo_dato=datos.tipo_dato,
            obligatorio=datos.obligatorio,
            orden=datos.orden,
            configuracion=datos.configuracion,
            activo=datos.activo,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="crear_campo_tramite",
            modulo="gestion_seguimiento",
            entidad="tramite_campo",
            id_entidad=campo.id_campo,
            detalle={
                "id_tramite": id_tramite,
                "clave": campo.clave,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(campo)

        return TramiteCampoResponse.model_validate(
            campo
        )

    except IntegrityError as exc:
        db.rollback()

        raise CampoDuplicadoError(
            "No fue posible registrar el campo."
        ) from exc

    except Exception:
        db.rollback()
        raise


def actualizar_campo_tramite(
    db: Session,
    *,
    id_tramite: int,
    id_campo: int,
    datos: TramiteCampoActualizarRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TramiteCampoResponse:
    """
    Actualiza un campo configurable.
    """
    if not datos.model_fields_set:
        raise TramiteServiceError(
            "Debe indicarse al menos un dato para actualizar."
        )

    campo = _obtener_campo_del_tramite(
        db,
        id_tramite=id_tramite,
        id_campo=id_campo,
    )

    if (
        "clave" in datos.model_fields_set
        and datos.clave is not None
        and datos.clave != campo.clave
    ):
        existente = obtener_campo_por_clave(
            db,
            id_tramite=id_tramite,
            clave=datos.clave,
        )

        if (
            existente is not None
            and existente.id_campo != id_campo
        ):
            raise CampoDuplicadoError(
                "Ya existe un campo con esa clave."
            )

    tipo_final = (
        datos.tipo_dato
        if (
            "tipo_dato" in datos.model_fields_set
            and datos.tipo_dato is not None
        )
        else campo.tipo_dato
    )

    configuracion_final = (
        datos.configuracion
        if "configuracion" in datos.model_fields_set
        else campo.configuracion
    )

    if tipo_final == "seleccion":
        if not configuracion_final:
            raise TramiteServiceError(
                "Un campo de selección requiere configuración."
            )

        opciones = configuracion_final.get(
            "opciones"
        )

        if not isinstance(opciones, list) or not opciones:
            raise TramiteServiceError(
                "Un campo de selección requiere una lista "
                "no vacía de opciones."
            )

    try:
        actualizar_campo(
            db,
            campo,
            clave=datos.clave,
            etiqueta=datos.etiqueta,
            descripcion=datos.descripcion,
            tipo_dato=datos.tipo_dato,
            obligatorio=datos.obligatorio,
            orden=datos.orden,
            configuracion=datos.configuracion,
            activo=datos.activo,
            actualizar_descripcion=(
                "descripcion" in datos.model_fields_set
            ),
            actualizar_configuracion=(
                "configuracion" in datos.model_fields_set
            ),
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="actualizar_campo_tramite",
            modulo="gestion_seguimiento",
            entidad="tramite_campo",
            id_entidad=id_campo,
            detalle={
                "id_tramite": id_tramite,
                "clave": campo.clave,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(campo)

        return TramiteCampoResponse.model_validate(
            campo
        )

    except IntegrityError as exc:
        db.rollback()

        raise CampoDuplicadoError(
            "No fue posible actualizar el campo."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ============================================================
# ETAPAS CONFIGURABLES
# ============================================================


def agregar_etapa_tramite(
    db: Session,
    *,
    id_tramite: int,
    datos: TramiteEtapaCrearRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TramiteEtapaResponse:
    """
    Registra una etapa únicamente cuando su definición
    institucional haya sido confirmada.

    El servicio no infiere unidades, nombres ni secuencias.
    """
    _obtener_tramite_o_error(
        db,
        id_tramite,
    )

    _validar_unidad_etapa(
        db,
        datos.id_unidad,
    )

    existente_orden = obtener_etapa_por_orden(
        db,
        id_tramite=id_tramite,
        orden=datos.orden,
    )

    if existente_orden is not None:
        raise EtapaDuplicadaError(
            "Ya existe una etapa con ese orden."
        )

    if (
        datos.activo
        and datos.es_inicial
        and obtener_etapa_inicial(
            db,
            id_tramite,
        ) is not None
    ):
        raise EtapaDuplicadaError(
            "El trámite ya tiene una etapa inicial activa."
        )

    if (
        datos.activo
        and datos.es_final
        and obtener_etapa_final(
            db,
            id_tramite,
        ) is not None
    ):
        raise EtapaDuplicadaError(
            "El trámite ya tiene una etapa final activa."
        )

    try:
        etapa = crear_etapa(
            db,
            id_tramite=id_tramite,
            id_unidad=datos.id_unidad,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            orden=datos.orden,
            es_inicial=datos.es_inicial,
            es_final=datos.es_final,
            activo=datos.activo,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="crear_etapa_tramite",
            modulo="gestion_seguimiento",
            entidad="tramite_etapa",
            id_entidad=etapa.id_etapa,
            detalle={
                "id_tramite": id_tramite,
                "nombre": etapa.nombre,
                "orden": etapa.orden,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(etapa)

        return TramiteEtapaResponse.model_validate(
            etapa
        )

    except IntegrityError as exc:
        db.rollback()

        raise EtapaDuplicadaError(
            "No fue posible registrar la etapa debido "
            "a un conflicto de configuración."
        ) from exc

    except Exception:
        db.rollback()
        raise


def actualizar_etapa_tramite(
    db: Session,
    *,
    id_tramite: int,
    id_etapa: int,
    datos: TramiteEtapaActualizarRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TramiteEtapaResponse:
    """
    Modifica una etapa previamente configurada.
    """
    if not datos.model_fields_set:
        raise TramiteServiceError(
            "Debe indicarse al menos un dato para actualizar."
        )

    etapa = _obtener_etapa_del_tramite(
        db,
        id_tramite=id_tramite,
        id_etapa=id_etapa,
    )

    if "id_unidad" in datos.model_fields_set:
        _validar_unidad_etapa(
            db,
            datos.id_unidad,
        )

    if (
        "orden" in datos.model_fields_set
        and datos.orden is not None
        and datos.orden != etapa.orden
    ):
        existente = obtener_etapa_por_orden(
            db,
            id_tramite=id_tramite,
            orden=datos.orden,
        )

        if (
            existente is not None
            and existente.id_etapa != id_etapa
        ):
            raise EtapaDuplicadaError(
                "Ya existe una etapa con ese orden."
            )

    es_inicial_final = (
        datos.es_inicial
        if (
            "es_inicial" in datos.model_fields_set
            and datos.es_inicial is not None
        )
        else etapa.es_inicial
    )

    es_final_final = (
        datos.es_final
        if (
            "es_final" in datos.model_fields_set
            and datos.es_final is not None
        )
        else etapa.es_final
    )

    activo_final = (
        datos.activo
        if (
            "activo" in datos.model_fields_set
            and datos.activo is not None
        )
        else etapa.activo
    )

    if es_inicial_final and activo_final:
        inicial_existente = obtener_etapa_inicial(
            db,
            id_tramite,
        )

        if (
            inicial_existente is not None
            and inicial_existente.id_etapa != id_etapa
        ):
            raise EtapaDuplicadaError(
                "El trámite ya tiene otra etapa inicial activa."
            )

    if es_final_final and activo_final:
        final_existente = obtener_etapa_final(
            db,
            id_tramite,
        )

        if (
            final_existente is not None
            and final_existente.id_etapa != id_etapa
        ):
            raise EtapaDuplicadaError(
                "El trámite ya tiene otra etapa final activa."
            )

    try:
        actualizar_etapa(
            db,
            etapa,
            id_unidad=datos.id_unidad,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            orden=datos.orden,
            es_inicial=datos.es_inicial,
            es_final=datos.es_final,
            activo=datos.activo,
            actualizar_unidad=(
                "id_unidad" in datos.model_fields_set
            ),
            actualizar_descripcion=(
                "descripcion" in datos.model_fields_set
            ),
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="actualizar_etapa_tramite",
            modulo="gestion_seguimiento",
            entidad="tramite_etapa",
            id_entidad=id_etapa,
            detalle={
                "id_tramite": id_tramite,
                "nombre": etapa.nombre,
                "orden": etapa.orden,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(etapa)

        return TramiteEtapaResponse.model_validate(
            etapa
        )

    except IntegrityError as exc:
        db.rollback()

        raise EtapaDuplicadaError(
            "No fue posible actualizar la etapa debido "
            "a un conflicto de configuración."
        ) from exc

    except Exception:
        db.rollback()
        raise