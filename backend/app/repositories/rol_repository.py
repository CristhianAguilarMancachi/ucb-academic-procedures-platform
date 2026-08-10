from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rol import Rol


def crear_rol(
    db: Session,
    *,
    nombre: str,
    descripcion: str | None = None,
    activo: bool = True,
) -> Rol:
    """
    Crea un rol dentro del catálogo.
    """
    rol = Rol(
        nombre=nombre.strip().lower(),
        descripcion=descripcion,
        activo=activo,
    )

    db.add(rol)
    db.flush()
    db.refresh(rol)

    return rol


def obtener_rol_por_id(
    db: Session,
    id_rol: int,
) -> Rol | None:
    """
    Obtiene un rol mediante su identificador.
    """
    return db.get(Rol, id_rol)


def obtener_rol_por_nombre(
    db: Session,
    nombre: str,
) -> Rol | None:
    """
    Busca un rol mediante su nombre normalizado.
    """
    consulta = select(
        Rol,
    ).where(
        Rol.nombre == nombre.strip().lower(),
    )

    return db.scalars(consulta).one_or_none()


def obtener_rol_activo_por_nombre(
    db: Session,
    nombre: str,
) -> Rol | None:
    """
    Busca un rol activo mediante su nombre.
    """
    consulta = select(
        Rol,
    ).where(
        Rol.nombre == nombre.strip().lower(),
        Rol.activo.is_(True),
    )

    return db.scalars(consulta).one_or_none()


def listar_roles(
    db: Session,
    *,
    solo_activos: bool = False,
) -> Sequence[Rol]:
    """
    Lista el catálogo de roles.
    """
    consulta = select(Rol)

    if solo_activos:
        consulta = consulta.where(
            Rol.activo.is_(True),
        )

    consulta = consulta.order_by(
        Rol.nombre.asc(),
    )

    return db.scalars(consulta).all()


def activar_rol(
    db: Session,
    rol: Rol,
) -> Rol:
    """
    Activa un rol.
    """
    rol.activo = True

    db.flush()
    db.refresh(rol)

    return rol


def desactivar_rol(
    db: Session,
    rol: Rol,
) -> Rol:
    """
    Desactiva un rol.
    """
    rol.activo = False

    db.flush()
    db.refresh(rol)

    return rol