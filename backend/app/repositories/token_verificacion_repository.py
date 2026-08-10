from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.token_verificacion_correo import (
    TokenVerificacionCorreo,
)


def crear_token_verificacion(
    db: Session,
    *,
    id_usuario_correo: int,
    token_hash: str,
    fecha_expiracion: datetime,
    direccion_ip_solicitud: str | None = None,
) -> TokenVerificacionCorreo:
    """
    Crea un token temporal para verificar un correo.
    """
    token = TokenVerificacionCorreo(
        id_usuario_correo=id_usuario_correo,
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


def obtener_token_verificacion_por_id(
    db: Session,
    id_token_verificacion: int,
) -> TokenVerificacionCorreo | None:
    """
    Obtiene un token mediante su identificador interno.
    """
    return db.get(
        TokenVerificacionCorreo,
        id_token_verificacion,
    )


def obtener_token_verificacion_por_hash(
    db: Session,
    token_hash: str,
    *,
    cargar_correo: bool = True,
) -> TokenVerificacionCorreo | None:
    """
    Busca un token mediante su hash SHA-256.
    """
    consulta = select(
        TokenVerificacionCorreo,
    ).where(
        TokenVerificacionCorreo.token_hash
        == token_hash,
    )

    if cargar_correo:
        consulta = consulta.options(
            selectinload(
                TokenVerificacionCorreo.usuario_correo,
            ),
        )

    return db.scalars(consulta).one_or_none()


def obtener_token_verificacion_disponible(
    db: Session,
    *,
    token_hash: str,
    fecha_actual: datetime,
) -> TokenVerificacionCorreo | None:
    """
    Busca un token que todavía pueda utilizarse.
    """
    consulta = (
        select(TokenVerificacionCorreo)
        .where(
            TokenVerificacionCorreo.token_hash
            == token_hash,
            TokenVerificacionCorreo.fecha_utilizacion.is_(
                None
            ),
            TokenVerificacionCorreo.fecha_revocacion.is_(
                None
            ),
            TokenVerificacionCorreo.fecha_expiracion
            > fecha_actual,
        )
        .options(
            selectinload(
                TokenVerificacionCorreo.usuario_correo,
            ),
        )
    )

    return db.scalars(consulta).one_or_none()


def listar_tokens_correo(
    db: Session,
    id_usuario_correo: int,
    *,
    solo_pendientes: bool = False,
    fecha_actual: datetime | None = None,
) -> Sequence[TokenVerificacionCorreo]:
    """
    Lista los tokens generados para un correo.
    """
    consulta = select(
        TokenVerificacionCorreo,
    ).where(
        TokenVerificacionCorreo.id_usuario_correo
        == id_usuario_correo,
    )

    if solo_pendientes:
        if fecha_actual is None:
            raise ValueError(
                "Debe indicarse fecha_actual al solicitar "
                "solamente tokens pendientes."
            )

        consulta = consulta.where(
            TokenVerificacionCorreo.fecha_utilizacion.is_(
                None
            ),
            TokenVerificacionCorreo.fecha_revocacion.is_(
                None
            ),
            TokenVerificacionCorreo.fecha_expiracion
            > fecha_actual,
        )

    consulta = consulta.order_by(
        TokenVerificacionCorreo.fecha_creacion.desc(),
    )

    return db.scalars(consulta).all()


def marcar_token_verificacion_utilizado(
    db: Session,
    token: TokenVerificacionCorreo,
    *,
    fecha_utilizacion: datetime,
) -> TokenVerificacionCorreo:
    """
    Marca un token como utilizado.
    """
    token.fecha_utilizacion = (
        fecha_utilizacion
    )

    db.flush()
    db.refresh(token)

    return token


def revocar_token_verificacion(
    db: Session,
    token: TokenVerificacionCorreo,
    *,
    fecha_revocacion: datetime,
) -> TokenVerificacionCorreo:
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


def revocar_tokens_pendientes_correo(
    db: Session,
    *,
    id_usuario_correo: int,
    fecha_revocacion: datetime,
) -> int:
    """
    Revoca los tokens anteriores pendientes antes de crear
    uno nuevo para el mismo correo.
    """
    resultado = db.execute(
        update(TokenVerificacionCorreo)
        .where(
            TokenVerificacionCorreo.id_usuario_correo
            == id_usuario_correo,
            TokenVerificacionCorreo.fecha_utilizacion.is_(
                None
            ),
            TokenVerificacionCorreo.fecha_revocacion.is_(
                None
            ),
        )
        .values(
            fecha_revocacion=fecha_revocacion,
        )
    )

    db.flush()

    return int(resultado.rowcount or 0)


def eliminar_tokens_verificacion_antiguos(
    db: Session,
    *,
    fecha_limite: datetime,
) -> int:
    """
    Elimina tokens expirados, utilizados o revocados cuya
    fecha de creación sea anterior al límite indicado.

    Esta función se utilizará posteriormente desde una tarea
    de mantenimiento.
    """
    resultado = db.execute(
        delete(TokenVerificacionCorreo)
        .where(
            TokenVerificacionCorreo.fecha_creacion
            < fecha_limite,
            (
                TokenVerificacionCorreo.fecha_expiracion
                < fecha_limite
            )
            | TokenVerificacionCorreo.fecha_utilizacion.is_not(
                None
            )
            | TokenVerificacionCorreo.fecha_revocacion.is_not(
                None
            ),
        )
    )

    db.flush()

    return int(resultado.rowcount or 0)