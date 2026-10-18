
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento import (
    tramite_repository as repo,
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
from app.schemas.gestion_seguimiento.tramite_requisito import (
    RequisitoEconomicoActualizarRequest,
    RequisitoEconomicoCrearRequest,
    RequisitoEconomicoResponse,
    TramiteRequisitoActualizarRequest,
    TramiteRequisitoCrearRequest,
    TramiteRequisitoResponse,
)
from app.services.auth.audit_service import registrar_accion_simple
from app.services.gestion_seguimiento.configuracion_flujo_service import (
    validar_condicion,
)


class TramiteServiceError(Exception):
    pass


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


class ConfiguracionEconomicaNoEncontradaError(TramiteServiceError):
    pass


class ConfiguracionEconomicaDuplicadaError(TramiteServiceError):
    pass


class CampoNoEncontradoError(TramiteServiceError):
    pass


class CampoDuplicadoError(TramiteServiceError):
    pass


class CampoNoPerteneceTramiteError(TramiteServiceError):
    pass


CAMPOS_ATENCION = (
    "tiempo_estimado",
    "canales_atencion",
    "instrucciones",
    "condiciones",
    "tipo_finalizacion",
    "tipo_intervencion",
)


# ============================================================
# VALIDACIONES Y HELPERS
# ============================================================

def _aplicar_extension(db, entidad, datos, campos):
    cambios = datos.model_dump(
        mode="json",
        exclude_unset=True,
    )

    for campo in campos:
        if campo not in cambios:
            continue

        valor = cambios[campo]

        if (
            campo == "requiere_presentacion_fisica"
            and valor is None
        ):
            raise ConfiguracionTramiteInvalidaError(
                "La presentación física no puede ser nula."
            )

        setattr(entidad, campo, valor)

    db.flush()


def _validar_extension_requisito(
    db,
    id_tramite,
    datos,
    requisito=None,
):
    valores = datos.model_dump(
        mode="json",
        exclude_unset=True,
    )

    if valores.get("id_etapa") is not None:
        raise ConfiguracionTramiteInvalidaError(
            "Los requisitos ya no se asocian a etapas. "
            "Elimina id_etapa de la petición."
        )

    activo = valores.get(
        "activo",
        getattr(requisito, "activo", True),
    )

    if activo is None:
        activo = getattr(requisito, "activo", True)

    condicion = valores.get(
        "condicion",
        getattr(requisito, "condicion", None),
    )

    if activo:
        campos = repo.listar_campos_tramite(
            db,
            id_tramite,
            solo_activos=True,
        )
        validar_condicion(condicion, campos)


def _validar_intervencion(tramite, datos):
    valores = datos.model_dump(exclude_unset=True)

    tipo = valores.get(
        "tipo_intervencion",
        getattr(tramite, "tipo_intervencion", "ninguna"),
    )

    finalizacion = valores.get(
        "tipo_finalizacion",
        getattr(tramite, "tipo_finalizacion", None),
    )

    if tipo not in {"ninguna", "firma", "conformidad"}:
        raise ConfiguracionTramiteInvalidaError(
            "Tipo de intervención inválido."
        )

    if (
        tipo != "ninguna"
        and finalizacion not in (
            None,
            "resultado_registrado",
        )
    ):
        raise ConfiguracionTramiteInvalidaError(
            "La firma o conformidad requiere finalización "
            "por resultado registrado."
        )


def _validar_estado_tramite(
    *,
    activo: bool,
    publicado: bool,
    permite_solicitudes: bool,
):
    if publicado and not activo:
        raise ConfiguracionTramiteInvalidaError(
            "Un trámite inactivo no puede estar publicado."
        )

    if permite_solicitudes and (
        not activo or not publicado
    ):
        raise ConfiguracionTramiteInvalidaError(
            "El trámite debe estar activo y publicado "
            "para permitir solicitudes."
        )


def _obtener_tramite_o_error(db, id_tramite):
    tramite = repo.obtener_tramite_por_id(db, id_tramite)

    if tramite is None:
        raise TramiteNoEncontradoError(
            "El trámite indicado no existe."
        )

    return tramite


def _obtener_requisito_del_tramite(
    db,
    *,
    id_tramite,
    id_requisito,
):
    requisito = repo.obtener_requisito_por_id(
        db,
        id_requisito,
    )

    if requisito is None:
        raise RequisitoNoEncontradoError(
            "El requisito indicado no existe."
        )

    if requisito.id_tramite != id_tramite:
        raise RequisitoNoPerteneceTramiteError(
            "El requisito pertenece a otro trámite."
        )

    return requisito


def _obtener_campo_del_tramite(
    db,
    *,
    id_tramite,
    id_campo,
):
    campo = repo.obtener_campo_por_id(db, id_campo)

    if campo is None:
        raise CampoNoEncontradoError(
            "El campo indicado no existe."
        )

    if campo.id_tramite != id_tramite:
        raise CampoNoPerteneceTramiteError(
            "El campo pertenece a otro trámite."
        )

    return campo


def _respuesta_tramite(tramite) -> TramiteResponse:
    """
    Construye la respuesta sin consultar Tramite.etapas.
    """

    return TramiteResponse.model_validate({
        "id_tramite": tramite.id_tramite,
        "nombre": tramite.nombre,
        "descripcion": tramite.descripcion,
        "activo": tramite.activo,
        "publicado": tramite.publicado,
        "permite_solicitudes": tramite.permite_solicitudes,
        "fecha_creacion": tramite.fecha_creacion,
        "fecha_actualizacion": tramite.fecha_actualizacion,
        "tiempo_estimado": tramite.tiempo_estimado,
        "canales_atencion": tramite.canales_atencion,
        "instrucciones": tramite.instrucciones,
        "condiciones": tramite.condiciones,
        "tipo_finalizacion": tramite.tipo_finalizacion,
        "tipo_intervencion": tramite.tipo_intervencion,
        "cantidad_requisitos_activos": sum(
            requisito.activo
            for requisito in tramite.requisitos
        ),
        "cantidad_etapas_activas": 0,
    })


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
    if repo.obtener_tramite_por_nombre(db, datos.nombre):
        raise TramiteDuplicadoError(
            "Ya existe un trámite con ese nombre."
        )

    _validar_estado_tramite(
        activo=datos.activo,
        publicado=datos.publicado,
        permite_solicitudes=datos.permite_solicitudes,
    )

    _validar_intervencion(None, datos)

    try:
        tramite = repo.crear_tramite(
            db,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            activo=datos.activo,
            publicado=datos.publicado,
            permite_solicitudes=datos.permite_solicitudes,
        )

        _aplicar_extension(
            db,
            tramite,
            datos,
            CAMPOS_ATENCION,
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
                "permite_solicitudes": tramite.permite_solicitudes,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(tramite)

        return _respuesta_tramite(tramite)

    except IntegrityError as exc:
        db.rollback()
        raise TramiteDuplicadoError(
            "No fue posible crear el trámite."
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
    tramites, total = repo.listar_tramites(
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
            _respuesta_tramite(tramite)
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
    tramite = repo.obtener_tramite_por_id_completo(
        db,
        id_tramite,
    )

    if tramite is None:
        raise TramiteNoEncontradoError(
            "El trámite indicado no existe."
        )

    requisitos = [
        TramiteRequisitoResponse.model_validate(requisito)
        for requisito in sorted(
            tramite.requisitos,
            key=lambda item: (
                item.orden,
                item.id_requisito,
            ),
        )
    ]

    campos = [
        TramiteCampoResponse.model_validate(campo)
        for campo in sorted(
            tramite.campos,
            key=lambda item: (
                item.orden,
                item.id_campo,
            ),
        )
    ]

    return TramiteDetalleResponse.model_validate({
        **_respuesta_tramite(tramite).model_dump(),
        "requisitos": requisitos,
        "campos": campos,
        "etapas": [],
    })


def actualizar_tramite_catalogo(
    db: Session,
    *,
    id_tramite: int,
    datos: TramiteActualizarRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> TramiteResponse:
    if not datos.model_fields_set:
        raise ActualizacionTramiteVaciaError(
            "Indica al menos un dato para actualizar."
        )

    tramite = _obtener_tramite_o_error(
        db,
        id_tramite,
    )

    if (
        datos.nombre is not None
        and datos.nombre.lower() != tramite.nombre.lower()
    ):
        existente = repo.obtener_tramite_por_nombre(
            db,
            datos.nombre,
        )

        if (
            existente is not None
            and existente.id_tramite != id_tramite
        ):
            raise TramiteDuplicadoError(
                "Ya existe un trámite con ese nombre."
            )

    if datos.activo is False:
        datos = datos.model_copy(
            update={
                "publicado": False,
                "permite_solicitudes": False,
            }
        )

    activo_final = (
        datos.activo
        if datos.activo is not None
        else tramite.activo
    )

    publicado_final = (
        datos.publicado
        if datos.publicado is not None
        else tramite.publicado
    )

    permite_final = (
        datos.permite_solicitudes
        if datos.permite_solicitudes is not None
        else tramite.permite_solicitudes
    )

    _validar_estado_tramite(
        activo=activo_final,
        publicado=publicado_final,
        permite_solicitudes=permite_final,
    )

    _validar_intervencion(tramite, datos)

    detalle_anterior = {
        "nombre": tramite.nombre,
        "descripcion": tramite.descripcion,
        "activo": tramite.activo,
        "publicado": tramite.publicado,
        "permite_solicitudes": tramite.permite_solicitudes,
        "tipo_finalizacion": tramite.tipo_finalizacion,
        "tipo_intervencion": tramite.tipo_intervencion,
    }

    try:
        repo.actualizar_tramite(
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

        _aplicar_extension(
            db,
            tramite,
            datos,
            CAMPOS_ATENCION,
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
                    "permite_solicitudes": tramite.permite_solicitudes,
                    "tipo_finalizacion": tramite.tipo_finalizacion,
                    "tipo_intervencion": tramite.tipo_intervencion,
                },
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(tramite)

        return _respuesta_tramite(tramite)

    except IntegrityError as exc:
        db.rollback()
        raise TramiteDuplicadoError(
            "No fue posible actualizar el trámite."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ============================================================
# CATÁLOGO PÚBLICO
# ============================================================

def obtener_catalogo_publicado(
    db: Session,
) -> ListaCatalogoTramitesResponse:
    tramites = repo.listar_catalogo_publicado(db)

    items = [
        TramiteResumenResponse.model_validate(tramite)
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
    tramite = repo.obtener_tramite_por_id_completo(
        db,
        id_tramite,
    )

    if (
        tramite is None
        or not tramite.activo
        or not tramite.publicado
    ):
        raise TramiteNoEncontradoError(
            "El trámite no está disponible en el catálogo."
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
        es_economico = bool(
            requisito.configuraciones_economicas
        )

        informacion_economica = None

        if es_economico:
            vigente = next(
                (
                    configuracion
                    for configuracion
                    in requisito.configuraciones_economicas
                    if (
                        configuracion.activo
                        and configuracion.gestion == gestion_actual
                    )
                ),
                None,
            )

            if vigente is not None:
                informacion_economica = (
                    TramiteCatalogoEconomicoResponse(
                        concepto=vigente.concepto,
                        monto=vigente.monto,
                        moneda=vigente.moneda,
                        gestion=vigente.gestion,
                    )
                )

        requisitos_visibles.append(
            TramiteCatalogoRequisitoResponse(
                id_requisito=requisito.id_requisito,
                nombre=requisito.nombre,
                descripcion=requisito.descripcion,
                obligatorio=requisito.obligatorio,
                orden=requisito.orden,
                requiere_presentacion_fisica=(
                    requisito.requiere_presentacion_fisica
                ),
                condicion=requisito.condicion,
                es_economico=es_economico,
                informacion_economica=informacion_economica,
                es_inicial=True,
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
        permite_solicitudes=tramite.permite_solicitudes,
        **{
            campo: getattr(tramite, campo)
            for campo in CAMPOS_ATENCION
        },
        pasos=[],
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
    _obtener_tramite_o_error(db, id_tramite)

    existente = repo.obtener_requisito_por_nombre(
        db,
        id_tramite=id_tramite,
        nombre=datos.nombre,
    )

    if existente is not None:
        raise RequisitoDuplicadoError(
            "Ya existe un requisito con ese nombre."
        )

    _validar_extension_requisito(
        db,
        id_tramite,
        datos,
    )

    try:
        requisito = repo.crear_requisito(
            db,
            id_tramite=id_tramite,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            obligatorio=datos.obligatorio,
            orden=datos.orden,
            activo=datos.activo,
        )

        _aplicar_extension(
            db,
            requisito,
            datos,
            ("requiere_presentacion_fisica", "condicion"),
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

        requisito = repo.obtener_requisito_por_id(
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
    if not datos.model_fields_set:
        raise TramiteServiceError(
            "Indica al menos un dato para actualizar."
        )

    requisito = _obtener_requisito_del_tramite(
        db,
        id_tramite=id_tramite,
        id_requisito=id_requisito,
    )

    if (
        datos.nombre is not None
        and datos.nombre.lower() != requisito.nombre.lower()
    ):
        existente = repo.obtener_requisito_por_nombre(
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

    _validar_extension_requisito(
        db,
        id_tramite,
        datos,
        requisito,
    )

    try:
        repo.actualizar_requisito(
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

        _aplicar_extension(
            db,
            requisito,
            datos,
            ("requiere_presentacion_fisica", "condicion"),
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="actualizar_requisito_tramite",
            modulo="gestion_seguimiento",
            entidad="tramite_requisito",
            id_entidad=id_requisito,
            detalle={"id_tramite": id_tramite},
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        requisito = repo.obtener_requisito_por_id(
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
# CONFIGURACIÓN ECONÓMICA
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
    _obtener_requisito_del_tramite(
        db,
        id_tramite=id_tramite,
        id_requisito=id_requisito,
    )

    existente = repo.obtener_configuracion_economica_por_gestion(
        db,
        id_requisito=id_requisito,
        gestion=datos.gestion,
    )

    if existente is not None:
        raise ConfiguracionEconomicaDuplicadaError(
            "Ya existe una configuración económica "
            "para esa gestión."
        )

    try:
        configuracion = repo.crear_configuracion_economica(
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
    if not datos.model_fields_set:
        raise TramiteServiceError(
            "Indica al menos un dato para actualizar."
        )

    _obtener_requisito_del_tramite(
        db,
        id_tramite=id_tramite,
        id_requisito=id_requisito,
    )

    configuracion = repo.obtener_configuracion_economica_por_id(
        db,
        id_requisito_economico,
    )

    if (
        configuracion is None
        or configuracion.id_requisito != id_requisito
    ):
        raise ConfiguracionEconomicaNoEncontradaError(
            "La configuración económica no pertenece "
            "al requisito indicado."
        )

    if (
        datos.gestion is not None
        and datos.gestion != configuracion.gestion
    ):
        existente = repo.obtener_configuracion_economica_por_gestion(
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
                "La gestión ya tiene una configuración económica."
            )

    try:
        repo.actualizar_configuracion_economica(
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
    _obtener_tramite_o_error(db, id_tramite)

    existente = repo.obtener_campo_por_clave(
        db,
        id_tramite=id_tramite,
        clave=datos.clave,
    )

    if existente is not None:
        raise CampoDuplicadoError(
            "Ya existe un campo con esa clave."
        )

    try:
        campo = repo.crear_campo(
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

        return TramiteCampoResponse.model_validate(campo)

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
    if not datos.model_fields_set:
        raise TramiteServiceError(
            "Indica al menos un dato para actualizar."
        )

    campo = _obtener_campo_del_tramite(
        db,
        id_tramite=id_tramite,
        id_campo=id_campo,
    )

    if (
        datos.clave is not None
        and datos.clave != campo.clave
    ):
        existente = repo.obtener_campo_por_clave(
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
        if datos.tipo_dato is not None
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

        opciones = configuracion_final.get("opciones")

        if not isinstance(opciones, list) or not opciones:
            raise TramiteServiceError(
                "El campo de selección requiere opciones."
            )

    try:
        repo.actualizar_campo(
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

        return TramiteCampoResponse.model_validate(campo)

    except IntegrityError as exc:
        db.rollback()
        raise CampoDuplicadoError(
            "No fue posible actualizar el campo."
        ) from exc

    except Exception:
        db.rollback()
        raise
