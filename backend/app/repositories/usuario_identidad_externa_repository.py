from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario_identidad_externa import (
    UsuarioIdentidadExterna,
)


# ============================================================
# CREACIÓN
# ============================================================

def crear_identidad_externa(
    db: Session,
    *,
    id_usuario: int,
    proveedor: str,
    identificador_proveedor: str,
) -> UsuarioIdentidadExterna:
    """
    Vincula una identidad externa con una cuenta existente.

    No realiza commit. La transacción debe ser confirmada por
    el servicio que coordina la autenticación.
    """
    identidad = UsuarioIdentidadExterna(
        id_usuario=id_usuario,
        proveedor=proveedor.strip().lower(),
        identificador_proveedor=(
            identificador_proveedor.strip()
        ),
    )

    db.add(identidad)
    db.flush()
    db.refresh(identidad)

    return identidad


# ============================================================
# CONSULTA POR PROVEEDOR E IDENTIFICADOR
# ============================================================

def obtener_identidad_externa(
    db: Session,
    *,
    proveedor: str,
    identificador_proveedor: str,
) -> UsuarioIdentidadExterna | None:
    """
    Busca una identidad externa mediante el identificador
    estable entregado por el proveedor.
    """
    consulta = select(
        UsuarioIdentidadExterna
    ).where(
        UsuarioIdentidadExterna.proveedor
        == proveedor.strip().lower(),

        UsuarioIdentidadExterna.identificador_proveedor
        == identificador_proveedor.strip(),
    )

    return (
        db
        .scalars(consulta)
        .one_or_none()
    )


# ============================================================
# CONSULTA POR USUARIO
# ============================================================

def obtener_identidad_usuario_proveedor(
    db: Session,
    *,
    id_usuario: int,
    proveedor: str,
) -> UsuarioIdentidadExterna | None:
    """
    Busca si una cuenta interna ya tiene una identidad
    asociada al proveedor indicado.
    """
    consulta = select(
        UsuarioIdentidadExterna
    ).where(
        UsuarioIdentidadExterna.id_usuario
        == id_usuario,

        UsuarioIdentidadExterna.proveedor
        == proveedor.strip().lower(),
    )

    return (
        db
        .scalars(consulta)
        .one_or_none()
    )


# ============================================================
# EXISTENCIA
# ============================================================

def existe_identidad_externa(
    db: Session,
    *,
    proveedor: str,
    identificador_proveedor: str,
) -> bool:
    """
    Indica si la identidad externa ya está vinculada.
    """
    consulta = select(
        select(
            UsuarioIdentidadExterna.id_usuario_identidad
        )
        .where(
            UsuarioIdentidadExterna.proveedor
            == proveedor.strip().lower(),

            UsuarioIdentidadExterna.identificador_proveedor
            == identificador_proveedor.strip(),
        )
        .exists()
    )

    return bool(
        db.scalar(consulta)
    )