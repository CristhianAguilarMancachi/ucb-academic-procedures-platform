from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.usuario_correo import UsuarioCorreo


def crear_correo(
    db: Session,
    *,
    id_usuario: int,
    correo: str,
    tipo: str,
    es_principal: bool = False,
    verificado: bool = False,
    fecha_verificacion: datetime | None = None,
) -> UsuarioCorreo:
    """
    Crea un correo asociado a una cuenta.

    Si el correo se crea como verificado, debe recibirse también
    su fecha de verificación.
    """
    usuario_correo = UsuarioCorreo(
        id_usuario=id_usuario,
        correo=correo.strip(),
        tipo=tipo,
        es_principal=es_principal,
        verificado=verificado,
        activo=True,
        fecha_verificacion=fecha_verificacion,
    )

    db.add(usuario_correo)
    db.flush()
    db.refresh(usuario_correo)

    return usuario_correo


def obtener_correo_por_id(
    db: Session,
    id_usuario_correo: int,
    *,
    bloquear: bool = False,
) -> UsuarioCorreo | None:
    """
    Obtiene un correo mediante su identificador.
    """
    return db.get(
        UsuarioCorreo,
        id_usuario_correo,
        with_for_update=bloquear,
        populate_existing=bloquear,
    )


def obtener_correo_por_id_y_usuario(
    db: Session,
    *,
    id_usuario_correo: int,
    id_usuario: int,
) -> UsuarioCorreo | None:
    """
    Obtiene un correo solamente si pertenece al usuario indicado.
    """
    consulta = select(
        UsuarioCorreo,
    ).where(
        UsuarioCorreo.id_usuario_correo
        == id_usuario_correo,
        UsuarioCorreo.id_usuario
        == id_usuario,
    )

    return db.scalars(consulta).one_or_none()


def obtener_correo_por_direccion(
    db: Session,
    correo: str,
) -> UsuarioCorreo | None:
    """
    Busca un correo sin distinguir mayúsculas y minúsculas.
    """
    consulta = select(
        UsuarioCorreo,
    ).where(
        UsuarioCorreo.correo == correo.strip(),
    )

    return db.scalars(consulta).one_or_none()


def obtener_correo_activo_por_direccion(
    db: Session,
    correo: str,
) -> UsuarioCorreo | None:
    """
    Busca un correo que esté activo.
    """
    consulta = select(
        UsuarioCorreo,
    ).where(
        UsuarioCorreo.correo == correo.strip(),
        UsuarioCorreo.activo.is_(True),
    )

    return db.scalars(consulta).one_or_none()


def existe_correo(
    db: Session,
    correo: str,
) -> bool:
    """
    Comprueba si el correo ya está registrado.
    """
    consulta = select(
        select(UsuarioCorreo.id_usuario_correo)
        .where(
            UsuarioCorreo.correo == correo.strip(),
        )
        .exists()
    )

    return bool(db.scalar(consulta))


def listar_correos_usuario(
    db: Session,
    id_usuario: int,
    *,
    solo_activos: bool = False,
) -> Sequence[UsuarioCorreo]:
    """
    Lista los correos asociados a una cuenta.
    """
    consulta = select(
        UsuarioCorreo,
    ).where(
        UsuarioCorreo.id_usuario == id_usuario,
    )

    if solo_activos:
        consulta = consulta.where(
            UsuarioCorreo.activo.is_(True),
        )

    consulta = consulta.order_by(
        UsuarioCorreo.es_principal.desc(),
        UsuarioCorreo.fecha_creacion.asc(),
    )

    return db.scalars(consulta).all()


def obtener_correo_principal(
    db: Session,
    id_usuario: int,
) -> UsuarioCorreo | None:
    """
    Devuelve el correo principal activo de una cuenta.
    """
    consulta = select(
        UsuarioCorreo,
    ).where(
        UsuarioCorreo.id_usuario == id_usuario,
        UsuarioCorreo.es_principal.is_(True),
        UsuarioCorreo.activo.is_(True),
    )

    return db.scalars(consulta).one_or_none()


def marcar_correo_verificado(
    db: Session,
    usuario_correo: UsuarioCorreo,
    *,
    fecha_verificacion: datetime,
) -> UsuarioCorreo:
    """
    Marca un correo como verificado.
    """
    usuario_correo.verificado = True
    usuario_correo.fecha_verificacion = (
        fecha_verificacion
    )

    db.flush()
    db.refresh(usuario_correo)

    return usuario_correo


def establecer_correo_principal(
    db: Session,
    *,
    usuario_correo: UsuarioCorreo,
) -> UsuarioCorreo:
    """
    Establece un correo activo y verificado como principal.

    Desmarca previamente cualquier otro correo principal del
    mismo usuario dentro de la misma transacción.
    """
    db.execute(
        update(UsuarioCorreo)
        .where(
            UsuarioCorreo.id_usuario
            == usuario_correo.id_usuario,
            UsuarioCorreo.id_usuario_correo
            != usuario_correo.id_usuario_correo,
            UsuarioCorreo.es_principal.is_(True),
        )
        .values(
            es_principal=False,
        )
    )

    usuario_correo.es_principal = True

    db.flush()
    db.refresh(usuario_correo)

    return usuario_correo


def desactivar_correo(
    db: Session,
    usuario_correo: UsuarioCorreo,
) -> UsuarioCorreo:
    """
    Desactiva un correo y evita que continúe como principal.
    """
    usuario_correo.activo = False
    usuario_correo.es_principal = False

    db.flush()
    db.refresh(usuario_correo)

    return usuario_correo


def reactivar_correo(
    db: Session,
    usuario_correo: UsuarioCorreo,
) -> UsuarioCorreo:
    """
    Reactiva un correo previamente desactivado.
    """
    usuario_correo.activo = True

    db.flush()
    db.refresh(usuario_correo)

    return usuario_correo


def contar_correos_activos(
    db: Session,
    id_usuario: int,
) -> int:
    """
    Cuenta los correos activos asociados a una cuenta.
    """
    from sqlalchemy import func

    consulta = select(
        func.count(
            UsuarioCorreo.id_usuario_correo
        )
    ).where(
        UsuarioCorreo.id_usuario == id_usuario,
        UsuarioCorreo.activo.is_(True),
    )

    return int(db.scalar(consulta) or 0)
