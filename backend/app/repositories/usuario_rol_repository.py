from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.usuario_rol import UsuarioRol


def crear_asignacion_rol(
    db: Session,
    *,
    id_usuario: int,
    id_rol: int,
    asignado_por: int | None = None,
) -> UsuarioRol:
    """
    Asigna un rol a una cuenta.

    El rol inicial de solicitante puede tener asignado_por=None.
    """
    asignacion = UsuarioRol(
        id_usuario=id_usuario,
        id_rol=id_rol,
        activo=True,
        asignado_por=asignado_por,
        fecha_revocacion=None,
    )

    db.add(asignacion)
    db.flush()
    db.refresh(asignacion)

    return asignacion


def obtener_asignacion_por_id(
    db: Session,
    id_usuario_rol: int,
) -> UsuarioRol | None:
    """
    Obtiene una asignación de rol mediante su identificador.
    """
    consulta = (
        select(UsuarioRol)
        .where(
            UsuarioRol.id_usuario_rol
            == id_usuario_rol,
        )
        .options(
            selectinload(
                UsuarioRol.rol,
            ),
        )
    )

    return db.scalars(consulta).one_or_none()


def obtener_asignacion(
    db: Session,
    *,
    id_usuario: int,
    id_rol: int,
) -> UsuarioRol | None:
    """
    Busca la relación concreta entre un usuario y un rol.
    """
    consulta = (
        select(UsuarioRol)
        .where(
            UsuarioRol.id_usuario == id_usuario,
            UsuarioRol.id_rol == id_rol,
        )
        .options(
            selectinload(
                UsuarioRol.rol,
            ),
        )
    )

    return db.scalars(consulta).one_or_none()


def listar_roles_usuario(
    db: Session,
    id_usuario: int,
    *,
    solo_activos: bool = False,
) -> Sequence[UsuarioRol]:
    """
    Lista las asignaciones de rol de una cuenta.
    """
    consulta = (
        select(UsuarioRol)
        .where(
            UsuarioRol.id_usuario == id_usuario,
        )
        .options(
            selectinload(
                UsuarioRol.rol,
            ),
        )
        .order_by(
            UsuarioRol.fecha_asignacion.asc(),
        )
    )

    if solo_activos:
        consulta = consulta.where(
            UsuarioRol.activo.is_(True),
            UsuarioRol.fecha_revocacion.is_(None),
        )

    return db.scalars(consulta).all()


def obtener_nombres_roles_activos(
    db: Session,
    id_usuario: int,
) -> list[str]:
    """
    Devuelve los nombres de los roles activos de una cuenta.
    """
    from app.models.rol import Rol

    consulta = (
        select(Rol.nombre)
        .join(
            UsuarioRol,
            UsuarioRol.id_rol == Rol.id_rol,
        )
        .where(
            UsuarioRol.id_usuario == id_usuario,
            UsuarioRol.activo.is_(True),
            UsuarioRol.fecha_revocacion.is_(None),
            Rol.activo.is_(True),
        )
        .order_by(
            Rol.nombre.asc(),
        )
    )

    return list(db.scalars(consulta).all())


def usuario_tiene_rol(
    db: Session,
    *,
    id_usuario: int,
    nombre_rol: str,
) -> bool:
    """
    Comprueba si una cuenta tiene un rol activo determinado.
    """
    from app.models.rol import Rol

    consulta = select(
        select(UsuarioRol.id_usuario_rol)
        .join(
            Rol,
            Rol.id_rol == UsuarioRol.id_rol,
        )
        .where(
            UsuarioRol.id_usuario == id_usuario,
            UsuarioRol.activo.is_(True),
            UsuarioRol.fecha_revocacion.is_(None),
            Rol.nombre == nombre_rol.strip().lower(),
            Rol.activo.is_(True),
        )
        .exists()
    )

    return bool(db.scalar(consulta))


def revocar_asignacion(
    db: Session,
    asignacion: UsuarioRol,
    *,
    fecha_revocacion: datetime,
) -> UsuarioRol:
    """
    Revoca una asignación de rol.
    """
    asignacion.activo = False
    asignacion.fecha_revocacion = (
        fecha_revocacion
    )

    db.flush()
    db.refresh(asignacion)

    return asignacion


def reactivar_asignacion(
    db: Session,
    asignacion: UsuarioRol,
) -> UsuarioRol:
    """
    Reactiva una relación de rol previamente revocada.
    """
    asignacion.activo = True
    asignacion.fecha_revocacion = None

    db.flush()
    db.refresh(asignacion)

    return asignacion