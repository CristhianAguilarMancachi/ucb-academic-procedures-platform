from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.usuario_rol import UsuarioRol
from app.repositories.rol_repository import (
    listar_roles,
    obtener_rol_activo_por_nombre,
    obtener_rol_por_id,
)
from app.repositories.usuario_repository import (
    obtener_usuario_por_id,
)
from app.repositories.usuario_rol_repository import (
    bloquear_administracion,
    contar_otros_administradores,
    usuario_tiene_rol,
    crear_asignacion_rol,
    obtener_asignacion,
    reactivar_asignacion,
    revocar_asignacion,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)


class RoleServiceError(Exception):
    """
    Error base del servicio de roles.
    """


class RolNoEncontradoError(RoleServiceError):
    """
    El rol solicitado no existe o está inactivo.
    """


class UsuarioNoEncontradoError(RoleServiceError):
    """
    El usuario solicitado no existe.
    """


class RolYaAsignadoError(RoleServiceError):
    """
    El usuario ya posee el rol activo.
    """


class RolNoAsignadoError(RoleServiceError):
    """
    El usuario no posee la asignación indicada.
    """


class UltimoAdministradorError(RoleServiceError):
    """
    Impide revocar el rol al último administrador activo.
    """


def proteger_ultimo_administrador(db: Session, usuario: Usuario) -> None:
    if (usuario.estado == "activo"
            and usuario_tiene_rol(db, id_usuario=usuario.id_usuario, nombre_rol="administrador")
            and contar_otros_administradores(db, usuario.id_usuario) == 0):
        raise UltimoAdministradorError(
            "La operación dejaría el sistema sin un administrador activo con correo verificado."
        )


def obtener_rol_predeterminado(
    db: Session,
) -> Rol:
    """
    Obtiene el rol que se asigna automáticamente durante
    el registro de una cuenta.
    """
    rol = obtener_rol_activo_por_nombre(
        db,
        "solicitante",
    )

    if rol is None:
        raise RolNoEncontradoError(
            "No se encontró el rol solicitante activo."
        )

    return rol


def asignar_rol_solicitante(
    db: Session,
    *,
    id_usuario: int,
) -> UsuarioRol:
    """
    Asigna el rol inicial de solicitante.

    Esta operación se usa durante el registro, por lo que
    asignado_por queda en None.
    """
    rol = obtener_rol_predeterminado(db)

    asignacion = obtener_asignacion(
        db,
        id_usuario=id_usuario,
        id_rol=rol.id_rol,
    )

    if asignacion is not None:
        if asignacion.activo and asignacion.fecha_revocacion is None:
            return asignacion

        return reactivar_asignacion(
            db,
            asignacion,
        )

    return crear_asignacion_rol(
        db,
        id_usuario=id_usuario,
        id_rol=rol.id_rol,
        asignado_por=None,
    )


def asignar_rol_usuario(
    db: Session,
    *,
    id_usuario: int,
    id_rol: int,
    id_usuario_actor: int,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UsuarioRol:
    """
    Asigna o reactiva un rol desde administración.
    """
    bloquear_administracion(db)
    usuario = obtener_usuario_por_id(
        db,
        id_usuario,
        bloquear=True,
    )

    if usuario is None:
        raise UsuarioNoEncontradoError(
            "El usuario indicado no existe."
        )

    rol = obtener_rol_por_id(
        db,
        id_rol,
    )

    if rol is None or not rol.activo:
        raise RolNoEncontradoError(
            "El rol indicado no existe o está inactivo."
        )

    asignacion = obtener_asignacion(
        db,
        id_usuario=id_usuario,
        id_rol=id_rol,
    )

    if (
        asignacion is not None
        and asignacion.activo
        and asignacion.fecha_revocacion is None
    ):
        raise RolYaAsignadoError(
            "El usuario ya tiene asignado ese rol."
        )

    try:
        if asignacion is None:
            asignacion = crear_asignacion_rol(
                db,
                id_usuario=id_usuario,
                id_rol=id_rol,
                asignado_por=id_usuario_actor,
            )
        else:
            asignacion.asignado_por = id_usuario_actor
            asignacion = reactivar_asignacion(
                db,
                asignacion,
            )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="asignar_rol",
            modulo="autenticacion",
            entidad="usuario_rol",
            id_entidad=asignacion.id_usuario_rol,
            detalle={
                "id_usuario": id_usuario,
                "id_rol": id_rol,
                "nombre_rol": rol.nombre,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(asignacion)

        return asignacion

    except IntegrityError as exc:
        db.rollback()

        raise RoleServiceError(
            "No fue posible asignar el rol."
        ) from exc

    except Exception:
        db.rollback()
        raise


def revocar_rol_usuario(
    db: Session,
    *,
    id_usuario: int,
    id_rol: int,
    id_usuario_actor: int,
    motivo: str | None = None,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UsuarioRol:
    """
    Revoca un rol asignado a un usuario.
    """
    bloquear_administracion(db)
    usuario = obtener_usuario_por_id(
        db,
        id_usuario,
        bloquear=True,
    )

    if usuario is None:
        raise UsuarioNoEncontradoError(
            "El usuario indicado no existe."
        )

    rol = obtener_rol_por_id(
        db,
        id_rol,
    )

    if rol is None:
        raise RolNoEncontradoError(
            "El rol indicado no existe."
        )

    asignacion = obtener_asignacion(
        db,
        id_usuario=id_usuario,
        id_rol=id_rol,
    )

    if (
        asignacion is None
        or not asignacion.activo
        or asignacion.fecha_revocacion is not None
    ):
        raise RolNoAsignadoError(
            "El usuario no tiene activo ese rol."
        )

    if rol.nombre == "administrador":
        try:
            proteger_ultimo_administrador(db, usuario)
        except UltimoAdministradorError:
            db.rollback()
            raise

    try:
        asignacion = revocar_asignacion(
            db,
            asignacion,
            fecha_revocacion=utc_now(),
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="revocar_rol",
            modulo="autenticacion",
            entidad="usuario_rol",
            id_entidad=asignacion.id_usuario_rol,
            detalle={
                "id_usuario": id_usuario,
                "id_rol": id_rol,
                "nombre_rol": rol.nombre,
                "motivo": motivo,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(asignacion)

        return asignacion

    except Exception:
        db.rollback()
        raise


def obtener_roles_disponibles(
    db: Session,
) -> list[Rol]:
    """
    Obtiene el catálogo de roles activos.
    """
    return list(
        listar_roles(
            db,
            solo_activos=True,
        )
    )