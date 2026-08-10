from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.usuario import Usuario
from app.models.usuario_rol import UsuarioRol


def crear_usuario(
    db: Session,
    *,
    nombres: str,
    apellidos: str,
    contrasena_hash: str | None,
    estado: str = "pendiente_verificacion",
) -> Usuario:
    """
    Crea una cuenta de usuario y deja la transacción pendiente
    de confirmación por parte del servicio.
    """
    usuario = Usuario(
        nombres=nombres,
        apellidos=apellidos,
        contrasena_hash=contrasena_hash,
        estado=estado,
    )

    db.add(usuario)
    db.flush()
    db.refresh(usuario)

    return usuario


def obtener_usuario_por_id(
    db: Session,
    id_usuario: int,
) -> Usuario | None:
    """
    Obtiene un usuario sin cargar relaciones adicionales.
    """
    return db.get(Usuario, id_usuario)


def obtener_usuario_por_id_completo(
    db: Session,
    id_usuario: int,
) -> Usuario | None:
    """
    Obtiene una cuenta con correos, roles y sesiones.
    """
    consulta = (
        select(Usuario)
        .where(
            Usuario.id_usuario == id_usuario,
        )
        .options(
            selectinload(
                Usuario.correos,
            ),
            selectinload(
                Usuario.asignaciones_rol,
            ).selectinload(
                UsuarioRol.rol,
            ),
            selectinload(
                Usuario.sesiones,
            ),
        )
    )

    return db.scalars(consulta).one_or_none()


def obtener_usuario_por_correo(
    db: Session,
    correo: str,
    *,
    solo_correo_activo: bool = True,
) -> Usuario | None:
    """
    Busca una cuenta mediante cualquiera de sus correos.

    La comparación no distingue mayúsculas porque PostgreSQL
    utiliza CITEXT en usuario_correo.correo.
    """
    from app.models.usuario_correo import UsuarioCorreo

    consulta = (
        select(Usuario)
        .join(
            UsuarioCorreo,
            UsuarioCorreo.id_usuario == Usuario.id_usuario,
        )
        .where(
            UsuarioCorreo.correo == correo.strip(),
        )
        .options(
            selectinload(
                Usuario.correos,
            ),
            selectinload(
                Usuario.asignaciones_rol,
            ).selectinload(
                UsuarioRol.rol,
            ),
            selectinload(
                Usuario.sesiones,
            ),
        )
    )

    if solo_correo_activo:
        consulta = consulta.where(
            UsuarioCorreo.activo.is_(True),
        )

    return db.scalars(consulta).unique().one_or_none()


def existe_usuario(
    db: Session,
    id_usuario: int,
) -> bool:
    """
    Indica si existe una cuenta con el identificador recibido.
    """
    consulta = select(
        select(Usuario.id_usuario)
        .where(
            Usuario.id_usuario == id_usuario,
        )
        .exists()
    )

    return bool(db.scalar(consulta))


def listar_usuarios(
    db: Session,
    *,
    pagina: int = 1,
    por_pagina: int = 20,
    estado: str | None = None,
    texto_busqueda: str | None = None,
) -> tuple[Sequence[Usuario], int]:
    """
    Devuelve usuarios paginados y el total de coincidencias.

    Permite filtrar por estado y buscar por nombres,
    apellidos o correo.
    """
    from app.models.usuario_correo import UsuarioCorreo

    pagina = max(pagina, 1)
    por_pagina = min(max(por_pagina, 1), 100)

    filtros = []

    if estado is not None:
        filtros.append(
            Usuario.estado == estado,
        )

    consulta_ids = select(
        Usuario.id_usuario,
    )

    if texto_busqueda:
        patron = f"%{texto_busqueda.strip()}%"

        consulta_ids = (
            consulta_ids
            .outerjoin(
                UsuarioCorreo,
                UsuarioCorreo.id_usuario
                == Usuario.id_usuario,
            )
            .where(
                Usuario.nombres.ilike(patron)
                | Usuario.apellidos.ilike(patron)
                | UsuarioCorreo.correo.ilike(patron)
            )
            .distinct()
        )

    if filtros:
        consulta_ids = consulta_ids.where(*filtros)

    subconsulta_ids = consulta_ids.subquery()

    total = db.scalar(
        select(func.count())
        .select_from(subconsulta_ids)
    ) or 0

    consulta_usuarios = (
        select(Usuario)
        .join(
            subconsulta_ids,
            subconsulta_ids.c.id_usuario
            == Usuario.id_usuario,
        )
        .options(
            selectinload(
                Usuario.correos,
            ),
            selectinload(
                Usuario.asignaciones_rol,
            ).selectinload(
                UsuarioRol.rol,
            ),
        )
        .order_by(
            Usuario.fecha_creacion.desc(),
        )
        .offset(
            (pagina - 1) * por_pagina,
        )
        .limit(
            por_pagina,
        )
    )

    usuarios = db.scalars(
        consulta_usuarios
    ).unique().all()

    return usuarios, int(total)


def actualizar_datos_usuario(
    db: Session,
    usuario: Usuario,
    *,
    nombres: str | None = None,
    apellidos: str | None = None,
) -> Usuario:
    """
    Actualiza nombres y apellidos de una cuenta.
    """
    if nombres is not None:
        usuario.nombres = nombres

    if apellidos is not None:
        usuario.apellidos = apellidos

    db.flush()
    db.refresh(usuario)

    return usuario


def actualizar_estado_usuario(
    db: Session,
    usuario: Usuario,
    *,
    estado: str,
) -> Usuario:
    """
    Modifica el estado de una cuenta.
    """
    usuario.estado = estado

    db.flush()
    db.refresh(usuario)

    return usuario


def actualizar_contrasena(
    db: Session,
    usuario: Usuario,
    *,
    contrasena_hash: str,
) -> Usuario:
    """
    Sustituye el hash de contraseña de una cuenta.
    """
    usuario.contrasena_hash = contrasena_hash

    db.flush()
    db.refresh(usuario)

    return usuario


def actualizar_ultimo_acceso(
    db: Session,
    usuario: Usuario,
    *,
    fecha_ultimo_acceso,
) -> Usuario:
    """
    Registra la fecha del último inicio de sesión exitoso.
    """
    usuario.fecha_ultimo_acceso = fecha_ultimo_acceso

    db.flush()

    return usuario