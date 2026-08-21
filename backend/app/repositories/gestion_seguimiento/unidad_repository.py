from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.gestion_seguimiento.unidad_administrativa import (
    UnidadAdministrativa,
)
from app.models.gestion_seguimiento.usuario_unidad import (
    UsuarioUnidad,
)


# ============================================================
# UNIDADES ADMINISTRATIVAS
# ============================================================


def crear_unidad(
    db: Session,
    *,
    nombre: str,
    descripcion: str | None = None,
    activo: bool = True,
) -> UnidadAdministrativa:
    """
    Crea una unidad administrativa.

    La confirmación de la transacción corresponde al service.
    """
    unidad = UnidadAdministrativa(
        nombre=nombre,
        descripcion=descripcion,
        activo=activo,
    )

    db.add(unidad)
    db.flush()
    db.refresh(unidad)

    return unidad


def obtener_unidad_por_id(
    db: Session,
    id_unidad: int,
) -> UnidadAdministrativa | None:
    """
    Obtiene una unidad sin cargar relaciones adicionales.
    """
    return db.get(
        UnidadAdministrativa,
        id_unidad,
    )


def obtener_unidad_por_id_completa(
    db: Session,
    id_unidad: int,
) -> UnidadAdministrativa | None:
    """
    Obtiene una unidad junto con sus asociaciones de usuarios.
    """
    consulta = (
        select(UnidadAdministrativa)
        .where(
            UnidadAdministrativa.id_unidad == id_unidad,
        )
        .options(
            selectinload(
                UnidadAdministrativa.asignaciones_usuario,
            ),
        )
    )

    return db.scalars(
        consulta
    ).unique().one_or_none()


def obtener_unidad_por_nombre(
    db: Session,
    nombre: str,
) -> UnidadAdministrativa | None:
    """
    Busca una unidad por nombre ignorando diferencias de
    mayúsculas y minúsculas.
    """
    nombre_normalizado = nombre.strip().lower()

    consulta = select(
        UnidadAdministrativa
    ).where(
        func.lower(
            UnidadAdministrativa.nombre
        ) == nombre_normalizado
    )

    return db.scalars(
        consulta
    ).one_or_none()


def existe_unidad(
    db: Session,
    id_unidad: int,
) -> bool:
    """
    Indica si existe una unidad con el identificador recibido.
    """
    consulta = select(
        select(
            UnidadAdministrativa.id_unidad
        )
        .where(
            UnidadAdministrativa.id_unidad == id_unidad,
        )
        .exists()
    )

    return bool(db.scalar(consulta))


def listar_unidades(
    db: Session,
    *,
    pagina: int = 1,
    por_pagina: int = 20,
    solo_activas: bool = False,
    texto_busqueda: str | None = None,
) -> tuple[
    Sequence[UnidadAdministrativa],
    int,
]:
    """
    Lista unidades administrativas con filtros y paginación.
    """
    pagina = max(pagina, 1)
    por_pagina = min(
        max(por_pagina, 1),
        100,
    )

    filtros = []

    if solo_activas:
        filtros.append(
            UnidadAdministrativa.activo.is_(True)
        )

    if texto_busqueda:
        patron = f"%{texto_busqueda.strip()}%"

        filtros.append(
            UnidadAdministrativa.nombre.ilike(
                patron
            )
            | UnidadAdministrativa.descripcion.ilike(
                patron
            )
        )

    consulta_base = select(
        UnidadAdministrativa
    )

    if filtros:
        consulta_base = consulta_base.where(
            *filtros
        )

    subconsulta = consulta_base.with_only_columns(
        UnidadAdministrativa.id_unidad
    ).subquery()

    total = db.scalar(
        select(func.count())
        .select_from(subconsulta)
    ) or 0

    consulta = (
        consulta_base
        .order_by(
            UnidadAdministrativa.nombre.asc(),
        )
        .offset(
            (pagina - 1) * por_pagina,
        )
        .limit(
            por_pagina,
        )
    )

    unidades = db.scalars(
        consulta
    ).all()

    return unidades, int(total)


def actualizar_unidad(
    db: Session,
    unidad: UnidadAdministrativa,
    *,
    nombre: str | None = None,
    descripcion: str | None = None,
    activo: bool | None = None,
    actualizar_descripcion: bool = False,
) -> UnidadAdministrativa:
    """
    Modifica una unidad administrativa.

    actualizar_descripcion permite distinguir entre:
    - no modificar la descripción;
    - establecer explícitamente descripcion=None.
    """
    if nombre is not None:
        unidad.nombre = nombre

    if actualizar_descripcion:
        unidad.descripcion = descripcion

    if activo is not None:
        unidad.activo = activo

    db.flush()
    db.refresh(unidad)

    return unidad


# ============================================================
# ASOCIACIONES USUARIO ↔ UNIDAD
# ============================================================


def crear_asignacion_usuario_unidad(
    db: Session,
    *,
    id_usuario: int,
    id_unidad: int,
    asignado_por: int | None,
) -> UsuarioUnidad:
    """
    Asocia un usuario con una unidad administrativa.
    """
    asignacion = UsuarioUnidad(
        id_usuario=id_usuario,
        id_unidad=id_unidad,
        activo=True,
        asignado_por=asignado_por,
        fecha_revocacion=None,
    )

    db.add(asignacion)
    db.flush()
    db.refresh(asignacion)

    return asignacion


def obtener_asignacion_usuario_unidad_por_id(
    db: Session,
    id_usuario_unidad: int,
) -> UsuarioUnidad | None:
    """
    Obtiene una asociación mediante su identificador.
    """
    consulta = (
        select(UsuarioUnidad)
        .where(
            UsuarioUnidad.id_usuario_unidad
            == id_usuario_unidad,
        )
        .options(
            selectinload(
                UsuarioUnidad.unidad,
            ),
        )
    )

    return db.scalars(
        consulta
    ).one_or_none()


def obtener_asignacion_usuario_unidad(
    db: Session,
    *,
    id_usuario: int,
    id_unidad: int,
) -> UsuarioUnidad | None:
    """
    Busca una asociación concreta entre usuario y unidad.
    """
    consulta = (
        select(UsuarioUnidad)
        .where(
            UsuarioUnidad.id_usuario == id_usuario,
            UsuarioUnidad.id_unidad == id_unidad,
        )
        .options(
            selectinload(
                UsuarioUnidad.unidad,
            ),
        )
    )

    return db.scalars(
        consulta
    ).one_or_none()


def listar_unidades_usuario(
    db: Session,
    id_usuario: int,
    *,
    solo_activas: bool = False,
) -> Sequence[UsuarioUnidad]:
    """
    Lista las unidades asociadas a un usuario.
    """
    consulta = (
        select(UsuarioUnidad)
        .where(
            UsuarioUnidad.id_usuario == id_usuario,
        )
        .options(
            selectinload(
                UsuarioUnidad.unidad,
            ),
        )
        .order_by(
            UsuarioUnidad.fecha_asignacion.asc(),
        )
    )

    if solo_activas:
        consulta = consulta.where(
            UsuarioUnidad.activo.is_(True),
            UsuarioUnidad.fecha_revocacion.is_(None),
            UsuarioUnidad.unidad.has(
                UnidadAdministrativa.activo.is_(True)
            ),
        )

    return db.scalars(
        consulta
    ).all()


def listar_usuarios_unidad(
    db: Session,
    id_unidad: int,
    *,
    solo_activos: bool = False,
) -> Sequence[UsuarioUnidad]:
    """
    Lista las asociaciones de usuarios pertenecientes
    a una unidad administrativa.
    """
    consulta = (
        select(UsuarioUnidad)
        .where(
            UsuarioUnidad.id_unidad == id_unidad,
        )
        .order_by(
            UsuarioUnidad.fecha_asignacion.asc(),
        )
    )

    if solo_activos:
        consulta = consulta.where(
            UsuarioUnidad.activo.is_(True),
            UsuarioUnidad.fecha_revocacion.is_(None),
        )

    return db.scalars(
        consulta
    ).all()


def usuario_pertenece_unidad(
    db: Session,
    *,
    id_usuario: int,
    id_unidad: int,
) -> bool:
    """
    Comprueba si un usuario tiene una asociación activa
    con una unidad administrativa activa.
    """
    consulta = select(
        select(
            UsuarioUnidad.id_usuario_unidad
        )
        .join(
            UnidadAdministrativa,
            UnidadAdministrativa.id_unidad
            == UsuarioUnidad.id_unidad,
        )
        .where(
            UsuarioUnidad.id_usuario == id_usuario,
            UsuarioUnidad.id_unidad == id_unidad,
            UsuarioUnidad.activo.is_(True),
            UsuarioUnidad.fecha_revocacion.is_(None),
            UnidadAdministrativa.activo.is_(True),
        )
        .exists()
    )

    return bool(db.scalar(consulta))


def revocar_asignacion_usuario_unidad(
    db: Session,
    asignacion: UsuarioUnidad,
    *,
    fecha_revocacion: datetime,
) -> UsuarioUnidad:
    """
    Revoca una asociación usuario-unidad sin eliminarla.
    """
    asignacion.activo = False
    asignacion.fecha_revocacion = (
        fecha_revocacion
    )

    db.flush()
    db.refresh(asignacion)

    return asignacion


def reactivar_asignacion_usuario_unidad(
    db: Session,
    asignacion: UsuarioUnidad,
    *,
    asignado_por: int | None,
) -> UsuarioUnidad:
    """
    Reactiva una asociación previamente revocada.
    """
    asignacion.activo = True
    asignacion.fecha_revocacion = None
    asignacion.asignado_por = asignado_por

    db.flush()
    db.refresh(asignacion)

    return asignacion