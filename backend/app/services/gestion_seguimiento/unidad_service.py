from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.repositories.gestion_seguimiento.unidad_repository import (
    actualizar_unidad,
    crear_asignacion_usuario_unidad,
    crear_unidad,
    listar_unidades,
    obtener_asignacion_usuario_unidad,
    obtener_unidad_por_id,
    obtener_unidad_por_id_completa,
    obtener_unidad_por_nombre,
    reactivar_asignacion_usuario_unidad,
    revocar_asignacion_usuario_unidad,
)
from app.repositories.usuario_repository import (
    obtener_usuario_por_id,
)
from app.repositories.usuario_rol_repository import (
    usuario_tiene_rol,
)
from app.schemas.gestion_seguimiento.unidad import (
    ListaUnidadesResponse,
    UnidadActualizarRequest,
    UnidadCrearRequest,
    UnidadDetalleResponse,
    UnidadResponse,
    UsuarioUnidadResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)


class UnidadServiceError(Exception):
    """
    Error base para operaciones relacionadas con unidades.
    """


class UnidadNoEncontradaError(UnidadServiceError):
    """
    La unidad solicitada no existe.
    """


class UnidadDuplicadaError(UnidadServiceError):
    """
    Ya existe una unidad con el mismo nombre.
    """


class ActualizacionUnidadVaciaError(UnidadServiceError):
    """
    No se recibió ningún campo para actualizar.
    """


class UsuarioNoEncontradoError(UnidadServiceError):
    """
    El usuario que se intenta asociar no existe.
    """


class UsuarioSinRolAdministrativoError(UnidadServiceError):
    """
    El usuario no posee el rol requerido para pertenecer
    a una unidad administrativa.
    """


class UsuarioUnidadYaAsignadaError(UnidadServiceError):
    """
    El usuario ya se encuentra asociado activamente
    con la unidad.
    """


class UsuarioUnidadNoAsignadaError(UnidadServiceError):
    """
    No existe una asociación activa que pueda revocarse.
    """


# ============================================================
# CONSTRUCCIÓN DE RESPUESTAS
# ============================================================


def _construir_detalle_unidad(
    unidad,
) -> UnidadDetalleResponse:
    """
    Construye el detalle de una unidad incluyendo sus
    asociaciones de usuarios.
    """
    usuarios_asignados = [
        UsuarioUnidadResponse.model_validate(asignacion)
        for asignacion in unidad.asignaciones_usuario
    ]

    return UnidadDetalleResponse(
        id_unidad=unidad.id_unidad,
        nombre=unidad.nombre,
        descripcion=unidad.descripcion,
        activo=unidad.activo,
        fecha_creacion=unidad.fecha_creacion,
        fecha_actualizacion=unidad.fecha_actualizacion,
        usuarios_asignados=usuarios_asignados,
    )


# ============================================================
# UNIDADES ADMINISTRATIVAS
# ============================================================


def crear_unidad_administrativa(
    db: Session,
    *,
    datos: UnidadCrearRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UnidadResponse:
    """
    Registra una nueva unidad administrativa.
    """
    existente = obtener_unidad_por_nombre(
        db,
        datos.nombre,
    )

    if existente is not None:
        raise UnidadDuplicadaError(
            "Ya existe una unidad administrativa con ese nombre."
        )

    try:
        unidad = crear_unidad(
            db,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            activo=datos.activo,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="crear_unidad_administrativa",
            modulo="gestion_seguimiento",
            entidad="unidad_administrativa",
            id_entidad=unidad.id_unidad,
            detalle={
                "nombre": unidad.nombre,
                "activo": unidad.activo,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(unidad)

        return UnidadResponse.model_validate(
            unidad
        )

    except IntegrityError as exc:
        db.rollback()

        raise UnidadDuplicadaError(
            "No fue posible crear la unidad porque existe "
            "un registro con datos incompatibles."
        ) from exc

    except Exception:
        db.rollback()
        raise


def obtener_unidad_administrativa(
    db: Session,
    *,
    id_unidad: int,
) -> UnidadDetalleResponse:
    """
    Obtiene el detalle administrativo de una unidad.
    """
    unidad = obtener_unidad_por_id_completa(
        db,
        id_unidad,
    )

    if unidad is None:
        raise UnidadNoEncontradaError(
            "La unidad administrativa indicada no existe."
        )

    return _construir_detalle_unidad(
        unidad
    )


def listar_unidades_administrativas(
    db: Session,
    *,
    pagina: int = 1,
    por_pagina: int = 20,
    solo_activas: bool = False,
    texto_busqueda: str | None = None,
) -> ListaUnidadesResponse:
    """
    Lista unidades administrativas con filtros y paginación.
    """
    unidades, total = listar_unidades(
        db,
        pagina=pagina,
        por_pagina=por_pagina,
        solo_activas=solo_activas,
        texto_busqueda=texto_busqueda,
    )

    items = [
        UnidadResponse.model_validate(unidad)
        for unidad in unidades
    ]

    return ListaUnidadesResponse(
        items=items,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


def actualizar_unidad_administrativa(
    db: Session,
    *,
    id_unidad: int,
    datos: UnidadActualizarRequest,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UnidadResponse:
    """
    Modifica la configuración de una unidad administrativa.
    """
    if not datos.model_fields_set:
        raise ActualizacionUnidadVaciaError(
            "Debe indicarse al menos un dato para actualizar."
        )

    unidad = obtener_unidad_por_id(
        db,
        id_unidad,
    )

    if unidad is None:
        raise UnidadNoEncontradaError(
            "La unidad administrativa indicada no existe."
        )

    if (
        "nombre" in datos.model_fields_set
        and datos.nombre is not None
        and datos.nombre.lower() != unidad.nombre.lower()
    ):
        existente = obtener_unidad_por_nombre(
            db,
            datos.nombre,
        )

        if (
            existente is not None
            and existente.id_unidad != unidad.id_unidad
        ):
            raise UnidadDuplicadaError(
                "Ya existe una unidad administrativa "
                "con ese nombre."
            )

    detalle_anterior = {
        "nombre": unidad.nombre,
        "descripcion": unidad.descripcion,
        "activo": unidad.activo,
    }

    try:
        actualizar_unidad(
            db,
            unidad,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            activo=datos.activo,
            actualizar_descripcion=(
                "descripcion" in datos.model_fields_set
            ),
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="actualizar_unidad_administrativa",
            modulo="gestion_seguimiento",
            entidad="unidad_administrativa",
            id_entidad=unidad.id_unidad,
            detalle={
                "antes": detalle_anterior,
                "despues": {
                    "nombre": unidad.nombre,
                    "descripcion": unidad.descripcion,
                    "activo": unidad.activo,
                },
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(unidad)

        return UnidadResponse.model_validate(
            unidad
        )

    except IntegrityError as exc:
        db.rollback()

        raise UnidadDuplicadaError(
            "No fue posible actualizar la unidad porque "
            "existe un registro con datos incompatibles."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ============================================================
# ASOCIACIÓN USUARIO ↔ UNIDAD
# ============================================================


def asignar_usuario_unidad(
    db: Session,
    *,
    id_unidad: int,
    id_usuario: int,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UsuarioUnidadResponse:
    """
    Asocia un usuario con rol de personal administrativo
    a una unidad.

    La pertenencia a una unidad no sustituye al sistema de roles.
    """
    unidad = obtener_unidad_por_id(
        db,
        id_unidad,
    )

    if unidad is None:
        raise UnidadNoEncontradaError(
            "La unidad administrativa indicada no existe."
        )

    if not unidad.activo:
        raise UnidadServiceError(
            "No se pueden asignar usuarios a una unidad inactiva."
        )

    usuario = obtener_usuario_por_id(
        db,
        id_usuario,
    )

    if usuario is None:
        raise UsuarioNoEncontradoError(
            "El usuario indicado no existe."
        )

    es_personal_administrativo = usuario_tiene_rol(
        db,
        id_usuario=id_usuario,
        nombre_rol="personal_administrativo",
    )

    if not es_personal_administrativo:
        raise UsuarioSinRolAdministrativoError(
            "El usuario debe tener activo el rol "
            "'personal_administrativo' antes de ser "
            "asignado a una unidad."
        )

    asignacion = obtener_asignacion_usuario_unidad(
        db,
        id_usuario=id_usuario,
        id_unidad=id_unidad,
    )

    if (
        asignacion is not None
        and asignacion.activo
        and asignacion.fecha_revocacion is None
    ):
        raise UsuarioUnidadYaAsignadaError(
            "El usuario ya pertenece a esta unidad."
        )

    try:
        if asignacion is None:
            asignacion = crear_asignacion_usuario_unidad(
                db,
                id_usuario=id_usuario,
                id_unidad=id_unidad,
                asignado_por=id_usuario_actor,
            )
        else:
            asignacion = reactivar_asignacion_usuario_unidad(
                db,
                asignacion,
                asignado_por=id_usuario_actor,
            )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="asignar_usuario_unidad",
            modulo="gestion_seguimiento",
            entidad="usuario_unidad",
            id_entidad=asignacion.id_usuario_unidad,
            detalle={
                "id_usuario": id_usuario,
                "id_unidad": id_unidad,
                "nombre_unidad": unidad.nombre,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(asignacion)

        return UsuarioUnidadResponse.model_validate(
            asignacion
        )

    except IntegrityError as exc:
        db.rollback()

        raise UnidadServiceError(
            "No fue posible asociar el usuario con la unidad."
        ) from exc

    except Exception:
        db.rollback()
        raise


def revocar_usuario_unidad(
    db: Session,
    *,
    id_unidad: int,
    id_usuario: int,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UsuarioUnidadResponse:
    """
    Revoca la asociación de un usuario con una unidad
    sin eliminar el registro histórico.
    """
    unidad = obtener_unidad_por_id(
        db,
        id_unidad,
    )

    if unidad is None:
        raise UnidadNoEncontradaError(
            "La unidad administrativa indicada no existe."
        )

    usuario = obtener_usuario_por_id(
        db,
        id_usuario,
    )

    if usuario is None:
        raise UsuarioNoEncontradoError(
            "El usuario indicado no existe."
        )

    asignacion = obtener_asignacion_usuario_unidad(
        db,
        id_usuario=id_usuario,
        id_unidad=id_unidad,
    )

    if (
        asignacion is None
        or not asignacion.activo
        or asignacion.fecha_revocacion is not None
    ):
        raise UsuarioUnidadNoAsignadaError(
            "El usuario no posee una asociación activa "
            "con esta unidad."
        )

    try:
        asignacion = revocar_asignacion_usuario_unidad(
            db,
            asignacion,
            fecha_revocacion=utc_now(),
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="revocar_usuario_unidad",
            modulo="gestion_seguimiento",
            entidad="usuario_unidad",
            id_entidad=asignacion.id_usuario_unidad,
            detalle={
                "id_usuario": id_usuario,
                "id_unidad": id_unidad,
                "nombre_unidad": unidad.nombre,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(asignacion)

        return UsuarioUnidadResponse.model_validate(
            asignacion
        )

    except Exception:
        db.rollback()
        raise