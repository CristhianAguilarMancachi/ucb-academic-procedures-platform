from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.sesion_usuario import SesionUsuario


def crear_sesion(
    db: Session,
    *,
    id_usuario: int,
    identificador_sesion: UUID,
    refresh_token_hash: str,
    fecha_expiracion: datetime,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> SesionUsuario:
    """
    Crea una sesión autenticada.

    El refresh token original nunca se almacena; únicamente
    se guarda su hash SHA-256.
    """
    sesion = SesionUsuario(
        id_usuario=id_usuario,
        identificador_sesion=identificador_sesion,
        refresh_token_hash=refresh_token_hash,
        fecha_expiracion=fecha_expiracion,
        direccion_ip=direccion_ip,
        user_agent=user_agent,
    )

    db.add(sesion)
    db.flush()
    db.refresh(sesion)

    return sesion


def obtener_sesion_por_id(
    db: Session,
    id_sesion: int,
) -> SesionUsuario | None:
    """
    Obtiene una sesión mediante su identificador interno.
    """
    return db.get(
        SesionUsuario,
        id_sesion,
    )


def obtener_sesion_por_identificador(
    db: Session,
    identificador_sesion: UUID,
    *,
    cargar_usuario: bool = False,
) -> SesionUsuario | None:
    """
    Busca una sesión mediante su UUID público.
    """
    consulta = select(
        SesionUsuario,
    ).where(
        SesionUsuario.identificador_sesion
        == identificador_sesion,
    )

    if cargar_usuario:
        consulta = consulta.options(
            selectinload(
                SesionUsuario.usuario,
            ),
        )

    return db.scalars(consulta).one_or_none()


def obtener_sesion_por_identificador_y_usuario(
    db: Session,
    *,
    identificador_sesion: UUID,
    id_usuario: int,
) -> SesionUsuario | None:
    """
    Obtiene una sesión solamente si pertenece al usuario
    indicado.
    """
    consulta = select(
        SesionUsuario,
    ).where(
        SesionUsuario.identificador_sesion
        == identificador_sesion,
        SesionUsuario.id_usuario
        == id_usuario,
    )

    return db.scalars(consulta).one_or_none()


def obtener_sesion_por_refresh_hash(
    db: Session,
    refresh_token_hash: str,
    *,
    cargar_usuario: bool = True,
) -> SesionUsuario | None:
    """
    Busca la sesión asociada al hash de un refresh token.
    """
    consulta = select(
        SesionUsuario,
    ).where(
        SesionUsuario.refresh_token_hash
        == refresh_token_hash,
    )

    if cargar_usuario:
        consulta = consulta.options(
            selectinload(
                SesionUsuario.usuario,
            ),
        )

    return db.scalars(consulta).one_or_none()


def obtener_sesion_vigente_por_refresh_hash(
    db: Session,
    *,
    refresh_token_hash: str,
    fecha_actual: datetime,
) -> SesionUsuario | None:
    """
    Busca una sesión no revocada y no expirada mediante el
    hash del refresh token.
    """
    consulta = (
        select(SesionUsuario)
        .where(
            SesionUsuario.refresh_token_hash
            == refresh_token_hash,
            SesionUsuario.fecha_revocacion.is_(None),
            SesionUsuario.fecha_expiracion
            > fecha_actual,
        )
        .options(
            selectinload(
                SesionUsuario.usuario,
            ),
        )
    )

    return db.scalars(consulta).one_or_none()


def listar_sesiones_usuario(
    db: Session,
    id_usuario: int,
    *,
    solo_vigentes: bool = False,
    fecha_actual: datetime | None = None,
) -> Sequence[SesionUsuario]:
    """
    Lista las sesiones de una cuenta, ordenadas desde la más
    reciente.
    """
    consulta = select(
        SesionUsuario,
    ).where(
        SesionUsuario.id_usuario
        == id_usuario,
    )

    if solo_vigentes:
        if fecha_actual is None:
            raise ValueError(
                "Debe indicarse fecha_actual al solicitar "
                "solamente sesiones vigentes."
            )

        consulta = consulta.where(
            SesionUsuario.fecha_revocacion.is_(None),
            SesionUsuario.fecha_expiracion
            > fecha_actual,
        )

    consulta = consulta.order_by(
        SesionUsuario.fecha_ultima_actividad.desc(),
    )

    return db.scalars(consulta).all()


def contar_sesiones_vigentes(
    db: Session,
    *,
    id_usuario: int,
    fecha_actual: datetime,
) -> int:
    """
    Cuenta las sesiones no revocadas y no expiradas de una
    cuenta.
    """
    consulta = select(
        func.count(
            SesionUsuario.id_sesion
        )
    ).where(
        SesionUsuario.id_usuario
        == id_usuario,
        SesionUsuario.fecha_revocacion.is_(None),
        SesionUsuario.fecha_expiracion
        > fecha_actual,
    )

    return int(db.scalar(consulta) or 0)


def actualizar_actividad_sesion(
    db: Session,
    sesion: SesionUsuario,
    *,
    fecha_actividad: datetime,
) -> SesionUsuario:
    """
    Actualiza la última actividad registrada en una sesión.
    """
    sesion.fecha_ultima_actividad = fecha_actividad

    db.flush()

    return sesion


def rotar_refresh_token(
    db: Session,
    sesion: SesionUsuario,
    *,
    nuevo_refresh_token_hash: str,
    nueva_fecha_expiracion: datetime,
    fecha_actividad: datetime,
) -> SesionUsuario:
    """
    Sustituye el refresh token de una sesión.

    La rotación invalida automáticamente el valor anterior,
    porque su hash deja de estar almacenado.
    """
    sesion.refresh_token_hash = (
        nuevo_refresh_token_hash
    )
    sesion.fecha_expiracion = (
        nueva_fecha_expiracion
    )
    sesion.fecha_ultima_actividad = (
        fecha_actividad
    )

    db.flush()
    db.refresh(sesion)

    return sesion


def revocar_sesion(
    db: Session,
    sesion: SesionUsuario,
    *,
    fecha_revocacion: datetime,
    motivo_revocacion: str | None = None,
) -> SesionUsuario:
    """
    Revoca una sesión específica.
    """
    if sesion.fecha_revocacion is None:
        sesion.fecha_revocacion = (
            fecha_revocacion
        )
        sesion.motivo_revocacion = (
            motivo_revocacion
        )

        db.flush()
        db.refresh(sesion)

    return sesion


def revocar_sesiones_usuario(
    db: Session,
    *,
    id_usuario: int,
    fecha_revocacion: datetime,
    motivo_revocacion: str | None = None,
    excluir_identificador: UUID | None = None,
) -> int:
    """
    Revoca todas las sesiones vigentes de una cuenta.

    Opcionalmente conserva una sesión mediante su UUID.
    """
    condiciones = [
        SesionUsuario.id_usuario == id_usuario,
        SesionUsuario.fecha_revocacion.is_(None),
    ]

    if excluir_identificador is not None:
        condiciones.append(
            SesionUsuario.identificador_sesion
            != excluir_identificador
        )

    resultado = db.execute(
        update(SesionUsuario)
        .where(*condiciones)
        .values(
            fecha_revocacion=fecha_revocacion,
            motivo_revocacion=motivo_revocacion,
        )
    )

    db.flush()

    return int(resultado.rowcount or 0)


def revocar_sesiones_expiradas(
    db: Session,
    *,
    fecha_actual: datetime,
    motivo_revocacion: str = "sesion_expirada",
) -> int:
    """
    Marca como revocadas las sesiones que ya expiraron.

    Puede utilizarse desde una tarea periódica de limpieza.
    """
    resultado = db.execute(
        update(SesionUsuario)
        .where(
            SesionUsuario.fecha_revocacion.is_(None),
            SesionUsuario.fecha_expiracion
            <= fecha_actual,
        )
        .values(
            fecha_revocacion=fecha_actual,
            motivo_revocacion=motivo_revocacion,
        )
    )

    db.flush()

    return int(resultado.rowcount or 0)