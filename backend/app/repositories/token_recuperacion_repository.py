from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.token_recuperacion_contrasena import (
    TokenRecuperacionContrasena,
)


def crear_token_recuperacion(
    db: Session,
    *,
    id_usuario: int,
    token_hash: str,
    fecha_expiracion: datetime,
    direccion_ip_solicitud: str | None = None,
) -> TokenRecuperacionContrasena:
    """
    Crea un token temporal para recuperar una contraseña.
    """
    token = TokenRecuperacionContrasena(
        id_usuario=id_usuario,
        token_hash=token_hash,
        fecha_expiracion=fecha_expiracion,
        direccion_ip_solicitud=(
            direccion_ip_solicitud
        ),
    )

    db.add(token)
    db.flush()
    db.refresh(token)

    return token


def obtener_token_recuperacion_por_id(
    db: Session,
    id_token_recuperacion: int,
) -> TokenRecuperacionContrasena | None:
    """
    Obtiene un token mediante su identificador interno.
    """
    return db.get(
        TokenRecuperacionContrasena,
        id_token_recuperacion,
    )


def obtener_token_recuperacion_por_hash(
    db: Session,
    token_hash: str,
    *,
    cargar_usuario: bool = True,
) -> TokenRecuperacionContrasena | None:
    """
    Busca un token de recuperación mediante su hash.
    """
    consulta = select(
        TokenRecuperacionContrasena,
    ).where(
        TokenRecuperacionContrasena.token_hash
        == token_hash,
    )

    if cargar_usuario:
        consulta = consulta.options(
            selectinload(
                TokenRecuperacionContrasena.usuario,
            ),
        )

    return db.scalars(consulta).one_or_none()


def obtener_token_recuperacion_disponible(
    db: Session,
    *,
    token_hash: str,
    fecha_actual: datetime,
) -> TokenRecuperacionContrasena | None:
    """
    Busca un token no utilizado, no revocado y no expirado.
    """
    consulta = (
        select(TokenRecuperacionContrasena)
        .where(
            TokenRecuperacionContrasena.token_hash
            == token_hash,
            TokenRecuperacionContrasena.fecha_utilizacion.is_(
                None
            ),
            TokenRecuperacionContrasena.fecha_revocacion.is_(
                None
            ),
            TokenRecuperacionContrasena.fecha_expiracion
            > fecha_actual,
        )
        .options(
            selectinload(
                TokenRecuperacionContrasena.usuario,
            ),
        )
    )

    return db.scalars(consulta).one_or_none()


def listar_tokens_recuperacion_usuario(
    db: Session,
    id_usuario: int,
    *,
    solo_pendientes: bool = False,
    fecha_actual: datetime | None = None,
) -> Sequence[TokenRecuperacionContrasena]:
    """
    Lista los tokens de recuperación asociados a una cuenta.
    """
    consulta = select(
        TokenRecuperacionContrasena,
    ).where(
        TokenRecuperacionContrasena.id_usuario
        == id_usuario,
    )

    if solo_pendientes:
        if fecha_actual is None:
            raise ValueError(
                "Debe indicarse fecha_actual al solicitar "
                "solamente tokens pendientes."
            )

        consulta = consulta.where(
            TokenRecuperacionContrasena.fecha_utilizacion.is_(
                None
            ),
            TokenRecuperacionContrasena.fecha_revocacion.is_(
                None
            ),
            TokenRecuperacionContrasena.fecha_expiracion
            > fecha_actual,
        )

    consulta = consulta.order_by(
        TokenRecuperacionContrasena.fecha_creacion.desc(),
    )

    return db.scalars(consulta).all()


def marcar_token_recuperacion_utilizado(
    db: Session,
    token: TokenRecuperacionContrasena,
    *,
    fecha_utilizacion: datetime,
) -> TokenRecuperacionContrasena:
    """
    Marca un token como utilizado.
    """
    token.fecha_utilizacion = (
        fecha_utilizacion
    )

    db.flush()
    db.refresh(token)

    return token


def revocar_token_recuperacion(
    db: Session,
    token: TokenRecuperacionContrasena,
    *,
    fecha_revocacion: datetime,
) -> TokenRecuperacionContrasena:
    """
    Revoca un token específico.
    """
    if (
        token.fecha_utilizacion is None
        and token.fecha_revocacion is None
    ):
        token.fecha_revocacion = (
            fecha_revocacion
        )

        db.flush()
        db.refresh(token)

    return token


def revocar_tokens_pendientes_usuario(
    db: Session,
    *,
    id_usuario: int,
    fecha_revocacion: datetime,
) -> int:
    """
    Revoca tokens de recuperación anteriores antes de emitir
    uno nuevo para la misma cuenta.
    """
    resultado = db.execute(
        update(TokenRecuperacionContrasena)
        .where(
            TokenRecuperacionContrasena.id_usuario
            == id_usuario,
            TokenRecuperacionContrasena.fecha_utilizacion.is_(
                None
            ),
            TokenRecuperacionContrasena.fecha_revocacion.is_(
                None
            ),
        )
        .values(
            fecha_revocacion=fecha_revocacion,
        )
    )

    db.flush()

    return int(resultado.rowcount or 0)


def eliminar_tokens_recuperacion_antiguos(
    db: Session,
    *,
    fecha_limite: datetime,
) -> int:
    """
    Elimina tokens antiguos que ya expiraron, fueron usados
    o fueron revocados.
    """
    resultado = db.execute(
        delete(TokenRecuperacionContrasena)
        .where(
            TokenRecuperacionContrasena.fecha_creacion
            < fecha_limite,
            (
                TokenRecuperacionContrasena.fecha_expiracion
                < fecha_limite
            )
            | TokenRecuperacionContrasena.fecha_utilizacion.is_not(
                None
            )
            | TokenRecuperacionContrasena.fecha_revocacion.is_not(
                None
            ),
        )
    )

    db.flush()

    return int(resultado.rowcount or 0)