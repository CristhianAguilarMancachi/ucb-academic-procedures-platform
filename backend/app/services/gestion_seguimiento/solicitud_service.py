from __future__ import annotations

from datetime import date, datetime, timezone
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.gestion_seguimiento.solicitud import (
    Solicitud,
)
from app.models.gestion_seguimiento.tramite import (
    Tramite,
)
from app.models.gestion_seguimiento.tramite_campo import (
    TramiteCampo,
)
from app.repositories.gestion_seguimiento import (
    solicitud_repository,
    tramite_repository,
)
from app.schemas.gestion_seguimiento.solicitud import (
    ListaSolicitudesResponse,
    SolicitudActualizarRequest,
    SolicitudCrearRequest,
    SolicitudEnviarRequest,
    SolicitudResponse,
    SolicitudResumenResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)


class SolicitudServiceError(Exception):
    """Error base del servicio de solicitudes."""


class SolicitudNoEncontradaError(
    SolicitudServiceError
):
    """La solicitud no existe o no pertenece al usuario."""


class TramiteSolicitudNoEncontradoError(
    SolicitudServiceError
):
    """El trámite solicitado no existe."""


class TramiteNoDisponibleParaSolicitudError(
    SolicitudServiceError
):
    """El trámite no está habilitado para solicitudes."""


class SolicitudNoEsBorradorError(
    SolicitudServiceError
):
    """La operación solamente está permitida en borradores."""


class ActualizacionSolicitudVaciaError(
    SolicitudServiceError
):
    """No existen datos para actualizar."""


class CampoSolicitudInvalidoError(
    SolicitudServiceError
):
    """Un campo no pertenece al trámite o no está activo."""


class ValorCampoInvalidoError(
    SolicitudServiceError
):
    """El valor enviado no corresponde al tipo del campo."""


class ConfiguracionCampoInvalidaError(
    SolicitudServiceError
):
    """La configuración del campo no permite validarlo."""


class CamposObligatoriosFaltantesError(
    SolicitudServiceError
):
    """La solicitud tiene campos obligatorios sin completar."""


class ConfiguracionEconomicaIncompletaError(
    SolicitudServiceError
):
    """Un requisito económico no tiene configuración vigente."""


class FacturaSolicitudInvalidaError(
    SolicitudServiceError
):
    """La información de facturación indicada no es válida."""


class SolicitudInconsistenteError(
    SolicitudServiceError
):
    """La solicitud presenta una condición interna inesperada."""


# ============================================================
# HELPERS
# ============================================================


def _obtener_solicitud_del_usuario(
    db: Session,
    *,
    id_solicitud: int,
    id_solicitante: int,
    completa: bool = False,
) -> Solicitud:
    solicitud = (
        solicitud_repository
        .obtener_solicitud_usuario_por_id(
            db,
            id_solicitud=id_solicitud,
            id_solicitante=id_solicitante,
            completa=completa,
        )
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
    tramite = (
        tramite_repository
        .obtener_tramite_por_id(
            db,
            id_tramite,
        )
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
    """
    Valida un valor utilizando tipo_dato de tramite_campo.

    Retorna el valor normalizado que debe almacenarse.
    """
    tipo = campo.tipo_dato

    if tipo in {
        "texto",
        "texto_largo",
    }:
        if not isinstance(
            valor,
            str,
        ):
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
        if (
            not isinstance(
                valor,
                int,
            )
            or isinstance(
                valor,
                bool,
            )
        ):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe contener un número entero.'
            )

        return valor

    if tipo == "decimal":
        if (
            not isinstance(
                valor,
                (int, float),
            )
            or isinstance(
                valor,
                bool,
            )
        ):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe contener un número.'
            )

        if (
            isinstance(
                valor,
                float,
            )
            and not isfinite(valor)
        ):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" contiene un número inválido.'
            )

        return valor

    if tipo == "fecha":
        if not isinstance(
            valor,
            str,
        ):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe contener una fecha.'
            )

        valor_limpio = valor.strip()

        try:
            fecha = date.fromisoformat(
                valor_limpio
            )
        except ValueError as exc:
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe utilizar '
                "el formato YYYY-MM-DD."
            ) from exc

        return fecha.isoformat()

    if tipo == "booleano":
        if not isinstance(
            valor,
            bool,
        ):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe ser verdadero o falso.'
            )

        return valor

    if tipo == "seleccion":
        if not isinstance(
            valor,
            str,
        ):
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" debe contener '
                "una opción válida."
            )

        valor_limpio = valor.strip()

        if not valor_limpio:
            raise ValorCampoInvalidoError(
                f'El campo "{campo.etiqueta}" no puede estar vacío.'
            )

        configuracion = (
            campo.configuracion
            if isinstance(
                campo.configuracion,
                dict,
            )
            else {}
        )

        opciones = configuracion.get(
            "opciones"
        )

        if (
            not isinstance(
                opciones,
                list,
            )
            or not opciones
        ):
            raise ConfiguracionCampoInvalidaError(
                f'El campo "{campo.etiqueta}" no tiene '
                "opciones configuradas correctamente."
            )

        valores_permitidos: list[str] = []

        for opcion in opciones:
            if isinstance(
                opcion,
                str,
            ):
                valores_permitidos.append(
                    opcion
                )
                continue

            if isinstance(
                opcion,
                dict,
            ):
                valor_opcion = opcion.get(
                    "valor"
                )

                if isinstance(
                    valor_opcion,
                    str,
                ):
                    valores_permitidos.append(
                        valor_opcion
                    )
                    continue

            raise ConfiguracionCampoInvalidaError(
                f'El campo "{campo.etiqueta}" tiene '
                "una configuración de opciones inválida."
            )

        if valor_limpio not in valores_permitidos:
            raise ValorCampoInvalidoError(
                f'El valor indicado para "{campo.etiqueta}" '
                "no corresponde a una opción permitida."
            )

        return valor_limpio

    raise ConfiguracionCampoInvalidaError(
        f'El campo "{campo.etiqueta}" tiene '
        f'un tipo de dato no soportado: "{tipo}".'
    )


def _normalizar_datos_borrador(
    db: Session,
    *,
    id_tramite: int,
    datos,
) -> dict[int, Any]:
    """
    Valida todos los valores antes de modificar la base.

    Esto evita guardar una actualización parcial si uno de
    los campos del request es inválido.
    """
    campos = (
        tramite_repository
        .listar_campos_tramite(
            db,
            id_tramite,
            solo_activos=True,
        )
    )

    campos_por_id = {
        campo.id_campo: campo
        for campo in campos
    }

    resultado: dict[int, Any] = {}

    for dato in datos:
        if dato.id_campo in resultado:
            raise CampoSolicitudInvalidoError(
                "No puede enviarse el mismo campo "
                "más de una vez."
            )

        campo = campos_por_id.get(
            dato.id_campo
        )

        if campo is None:
            raise CampoSolicitudInvalidoError(
                "Uno de los campos enviados no pertenece "
                "al trámite o ya no está activo."
            )

        resultado[
            dato.id_campo
        ] = _validar_valor_campo(
            campo,
            dato.valor,
        )

    return resultado


def _normalizar_facturas_envio(
    datos: SolicitudEnviarRequest,
) -> dict[int, str]:
    """
    Convierte la lista de facturas a un diccionario por
    requisito y valida defensivamente duplicados.

    El schema ya realiza parte de esta validación, pero
    el service mantiene la regla de negocio.
    """
    resultado: dict[int, str] = {}
    numeros_utilizados: set[str] = set()

    for factura in datos.facturas:
        if factura.id_requisito in resultado:
            raise FacturaSolicitudInvalidaError(
                "No puede registrarse más de una factura "
                "para el mismo requisito."
            )

        numero_factura = (
            factura.numero_factura.strip()
        )

        if numero_factura in numeros_utilizados:
            raise FacturaSolicitudInvalidaError(
                "El mismo número de factura no puede "
                "asignarse a más de un requisito."
            )

        resultado[
            factura.id_requisito
        ] = numero_factura

        numeros_utilizados.add(
            numero_factura
        )

    return resultado


def _obtener_respuesta_completa(
    db: Session,
    id_solicitud: int,
) -> SolicitudResponse:
    solicitud = (
        solicitud_repository
        .obtener_solicitud_por_id_completa(
            db,
            id_solicitud,
        )
    )

    if solicitud is None:
        raise SolicitudNoEncontradaError(
            "La solicitud no existe."
        )

    return SolicitudResponse.model_validate(
        solicitud
    )


# ============================================================
# CREAR BORRADOR
# ============================================================


def crear_solicitud(
    db: Session,
    *,
    id_solicitante: int,
    datos: SolicitudCrearRequest,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SolicitudResponse:
    """
    Crea un nuevo borrador.

    No se generan requisitos ni estados administrativos.
    """
    _obtener_tramite_habilitado(
        db,
        datos.id_tramite,
    )

    try:
        solicitud = (
            solicitud_repository
            .crear_solicitud(
                db,
                id_solicitante=id_solicitante,
                id_tramite=datos.id_tramite,
            )
        )

        registrar_accion_simple(
            db,
            accion="crear_solicitud_borrador",
            modulo="gestion_seguimiento",
            id_usuario_actor=id_solicitante,
            entidad="solicitud",
            id_entidad=str(
                solicitud.id_solicitud
            ),
            exitoso=True,
            detalle={
                "id_tramite": datos.id_tramite,
                "estado": "borrador",
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        id_solicitud = (
            solicitud.id_solicitud
        )

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
    """
    Obtiene el detalle de una solicitud propia.
    """
    solicitud = _obtener_solicitud_del_usuario(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
        completa=True,
    )

    return SolicitudResponse.model_validate(
        solicitud
    )


def listar_mis_solicitudes(
    db: Session,
    *,
    id_solicitante: int,
    estado: str | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> ListaSolicitudesResponse:
    """
    Lista las solicitudes pertenecientes al usuario.
    """
    solicitudes, total = (
        solicitud_repository
        .listar_solicitudes_usuario(
            db,
            id_solicitante=id_solicitante,
            estado=estado,
            pagina=pagina,
            por_pagina=por_pagina,
        )
    )

    return ListaSolicitudesResponse(
        items=[
            SolicitudResumenResponse.model_validate(
                solicitud
            )
            for solicitud in solicitudes
        ],
        total=total,
        pagina=max(
            pagina,
            1,
        ),
        por_pagina=min(
            max(
                por_pagina,
                1,
            ),
            100,
        ),
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
    """
    Sustituye el conjunto de datos dinámicos del borrador.

    Si el cliente desea eliminar todos los valores opcionales,
    puede enviar:

        {"datos": []}
    """
    solicitud = _obtener_solicitud_del_usuario(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
    )

    _validar_solicitud_borrador(
        solicitud
    )

    if (
        "datos"
        not in datos.model_fields_set
        or datos.datos is None
    ):
        raise ActualizacionSolicitudVaciaError(
            "Debe proporcionar una lista de datos "
            "para actualizar el borrador."
        )

    valores_normalizados = (
        _normalizar_datos_borrador(
            db,
            id_tramite=solicitud.id_tramite,
            datos=datos.datos,
        )
    )

    try:
        datos_actuales = (
            solicitud_repository
            .listar_datos_solicitud(
                db,
                solicitud.id_solicitud,
            )
        )

        ids_recibidos = set(
            valores_normalizados.keys()
        )

        for dato_actual in datos_actuales:
            if (
                dato_actual.id_campo
                not in ids_recibidos
            ):
                solicitud_repository.eliminar_dato_solicitud(
                    db,
                    dato_actual,
                )

        for id_campo, valor in (
            valores_normalizados.items()
        ):
            solicitud_repository.guardar_dato_solicitud(
                db,
                id_solicitud=solicitud.id_solicitud,
                id_campo=id_campo,
                valor=valor,
            )

        registrar_accion_simple(
            db,
            accion="actualizar_solicitud_borrador",
            modulo="gestion_seguimiento",
            id_usuario_actor=id_solicitante,
            entidad="solicitud",
            id_entidad=str(
                solicitud.id_solicitud
            ),
            exitoso=True,
            detalle={
                "campos_guardados": sorted(
                    ids_recibidos
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
    """
    Elimina una solicitud únicamente mientras sea borrador.
    """
    solicitud = _obtener_solicitud_del_usuario(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
    )

    _validar_solicitud_borrador(
        solicitud
    )

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
            id_entidad=str(
                id_solicitud
            ),
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
    datos: SolicitudEnviarRequest,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SolicitudResponse:
    """
    Envía formalmente un borrador.

    La operación:
    - valida el trámite;
    - valida campos obligatorios;
    - valida nuevamente los valores guardados;
    - valida las facturas declaradas;
    - genera la fotografía de requisitos;
    - copia información económica vigente;
    - conserva el número de factura de requisitos económicos;
    - cambia el estado a pendiente_recepcion.

    La factura todavía NO se verifica contra la API.
    Esa operación corresponde a Fase 3.

    Todo se realiza dentro de una sola transacción.
    """
    solicitud = _obtener_solicitud_del_usuario(
        db,
        id_solicitud=id_solicitud,
        id_solicitante=id_solicitante,
    )

    _validar_solicitud_borrador(
        solicitud
    )

    _obtener_tramite_habilitado(
        db,
        solicitud.id_tramite,
    )

    campos = (
        tramite_repository
        .listar_campos_tramite(
            db,
            solicitud.id_tramite,
            solo_activos=True,
        )
    )

    datos_guardados = (
        solicitud_repository
        .listar_datos_solicitud(
            db,
            solicitud.id_solicitud,
        )
    )

    datos_por_campo = {
        dato.id_campo: dato
        for dato in datos_guardados
    }

    faltantes: list[str] = []

    for campo in campos:
        dato = datos_por_campo.get(
            campo.id_campo
        )

        if dato is None:
            if campo.obligatorio:
                faltantes.append(
                    campo.etiqueta
                )

            continue

        _validar_valor_campo(
            campo,
            dato.valor,
        )

    if faltantes:
        raise CamposObligatoriosFaltantesError(
            "Faltan campos obligatorios: "
            + ", ".join(
                faltantes
            )
            + "."
        )

    requisitos_generados = (
        solicitud_repository
        .contar_requisitos_solicitud(
            db,
            solicitud.id_solicitud,
        )
    )

    if requisitos_generados > 0:
        raise SolicitudInconsistenteError(
            "El borrador ya contiene una fotografía "
            "de requisitos y no puede enviarse nuevamente."
        )

    requisitos = (
        tramite_repository
        .listar_requisitos_tramite(
            db,
            solicitud.id_tramite,
            solo_activos=True,
        )
    )

    facturas_por_requisito = (
        _normalizar_facturas_envio(
            datos
        )
    )

    ids_requisitos_activos = {
        requisito.id_requisito
        for requisito in requisitos
    }

    ids_facturas_desconocidos = (
        set(
            facturas_por_requisito.keys()
        )
        - ids_requisitos_activos
    )

    if ids_facturas_desconocidos:
        raise FacturaSolicitudInvalidaError(
            "Se proporcionó una factura para un requisito "
            "que no pertenece al trámite o ya no está activo."
        )

    gestion_actual = datetime.now(
        ZoneInfo(
            "America/La_Paz"
        )
    ).year

    fecha_envio = datetime.now(
        timezone.utc
    )

    try:
        cantidad_facturas = 0

        for requisito in requisitos:
            # Un requisito se considera económico si alguna vez
            # tuvo configuración económica registrada.
            #
            # No miramos solamente configuraciones activas:
            # si existe configuración histórica pero falta una
            # vigente, eso debe producir un error de configuración
            # y no convertir silenciosamente el requisito en uno
            # no económico.
            es_economico = bool(
                requisito.configuraciones_economicas
            )

            configuracion_actual = None
            numero_factura = None

            if es_economico:
                configuracion_actual = (
                    tramite_repository
                    .obtener_configuracion_economica_por_gestion(
                        db,
                        id_requisito=(
                            requisito.id_requisito
                        ),
                        gestion=gestion_actual,
                    )
                )

                if (
                    configuracion_actual is None
                    or not configuracion_actual.activo
                ):
                    raise (
                        ConfiguracionEconomicaIncompletaError(
                            "El requisito "
                            f'"{requisito.nombre}" no tiene '
                            "configuración económica activa "
                            f"para la gestión {gestion_actual}."
                        )
                    )

                codigo_externo = (
                    configuracion_actual
                    .codigo_concepto_externo
                )

                if (
                    codigo_externo is None
                    or not codigo_externo.strip()
                ):
                    raise (
                        ConfiguracionEconomicaIncompletaError(
                            "El requisito "
                            f'"{requisito.nombre}" no tiene '
                            "un código de concepto externo "
                            "configurado para la validación "
                            "mediante API."
                        )
                    )

                numero_factura = (
                    facturas_por_requisito.get(
                        requisito.id_requisito
                    )
                )

                if (
                    requisito.obligatorio
                    and numero_factura is None
                ):
                    raise FacturaSolicitudInvalidaError(
                        "Debe registrar el número de factura "
                        "correspondiente al requisito económico "
                        f'"{requisito.nombre}".'
                    )

                if numero_factura is not None:
                    cantidad_facturas += 1

            elif (
                requisito.id_requisito
                in facturas_por_requisito
            ):
                raise FacturaSolicitudInvalidaError(
                    "Se proporcionó un número de factura para "
                    f'el requisito "{requisito.nombre}", '
                    "pero ese requisito no es económico."
                )

            solicitud_repository.crear_requisito_solicitud(
                db,
                id_solicitud=solicitud.id_solicitud,
                id_requisito_origen=(
                    requisito.id_requisito
                ),
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
                numero_factura=numero_factura,
            )

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
            id_entidad=str(
                solicitud.id_solicitud
            ),
            exitoso=True,
            detalle={
                "id_tramite": solicitud.id_tramite,
                "estado": "pendiente_recepcion",
                "gestion": gestion_actual,
                "cantidad_requisitos": len(
                    requisitos
                ),
                "cantidad_facturas": cantidad_facturas,
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