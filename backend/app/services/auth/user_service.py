from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models.usuario import Usuario
from app.repositories.sesion_usuario_repository import (
    contar_sesiones_vigentes,
    revocar_sesiones_usuario,
)
from app.repositories.usuario_repository import (
    actualizar_datos_usuario,
    actualizar_estado_usuario,
    listar_usuarios,
    obtener_usuario_por_id,
    obtener_usuario_por_id_completo,
)
from app.schemas.usuario import (
    ListaUsuariosResponse,
    UsuarioAdministradorDetalleResponse,
    UsuarioAutenticadoResponse,
    UsuarioResumenResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)


class UserServiceError(Exception):
    """
    Error base del servicio de usuarios.
    """


class UsuarioNoEncontradoError(UserServiceError):
    """
    El usuario solicitado no existe.
    """


class EstadoUsuarioInvalidoError(UserServiceError):
    """
    El estado solicitado no es válido.
    """


class ActualizacionUsuarioVaciaError(UserServiceError):
    """
    No se recibió ningún dato para actualizar.
    """


ESTADOS_USUARIO_VALIDOS = {
    "pendiente_verificacion",
    "activo",
    "bloqueado",
    "inactivo",
}


def _obtener_roles_activos(usuario: Usuario) -> list:
    """
    Obtiene los modelos Rol correspondientes a las
    asignaciones activas del usuario.
    """
    return [
        asignacion.rol
        for asignacion in usuario.asignaciones_rol
        if (
            asignacion.activo
            and asignacion.fecha_revocacion is None
            and asignacion.rol is not None
            and asignacion.rol.activo
        )
    ]


def construir_usuario_autenticado(
    usuario: Usuario,
) -> UsuarioAutenticadoResponse:
    """
    Construye la respuesta segura del perfil del usuario.
    """
    return UsuarioAutenticadoResponse(
        id_usuario=usuario.id_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        estado=usuario.estado,
        fecha_ultimo_acceso=usuario.fecha_ultimo_acceso,
        fecha_creacion=usuario.fecha_creacion,
        fecha_actualizacion=usuario.fecha_actualizacion,
        correos=usuario.correos,
        roles=_obtener_roles_activos(usuario),
    )


def obtener_perfil_usuario(
    db: Session,
    *,
    id_usuario: int,
) -> UsuarioAutenticadoResponse:
    """
    Obtiene el perfil completo del usuario autenticado.
    """
    usuario = obtener_usuario_por_id_completo(
        db,
        id_usuario,
    )

    if usuario is None:
        raise UsuarioNoEncontradoError(
            "No se encontró el usuario."
        )

    return construir_usuario_autenticado(usuario)


def actualizar_perfil_usuario(
    db: Session,
    *,
    usuario: Usuario,
    nombres: str | None = None,
    apellidos: str | None = None,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UsuarioAutenticadoResponse:
    """
    Actualiza los nombres y apellidos del usuario autenticado.
    """
    if nombres is None and apellidos is None:
        raise ActualizacionUsuarioVaciaError(
            "Debe indicarse al menos un dato para actualizar."
        )

    try:
        actualizar_datos_usuario(
            db,
            usuario,
            nombres=nombres,
            apellidos=apellidos,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=usuario.id_usuario,
            accion="actualizar_perfil",
            modulo="usuarios",
            entidad="usuario",
            id_entidad=usuario.id_usuario,
            detalle={
                "nombres_actualizados": nombres is not None,
                "apellidos_actualizados": apellidos is not None,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        usuario_actualizado = obtener_usuario_por_id_completo(
            db,
            usuario.id_usuario,
        )

        if usuario_actualizado is None:
            raise UsuarioNoEncontradoError(
                "No fue posible recuperar el usuario actualizado."
            )

        return construir_usuario_autenticado(
            usuario_actualizado
        )

    except Exception:
        db.rollback()
        raise


def obtener_usuario_administracion(
    db: Session,
    *,
    id_usuario: int,
) -> UsuarioAdministradorDetalleResponse:
    """
    Obtiene el detalle completo de una cuenta para
    administración.
    """
    usuario = obtener_usuario_por_id_completo(
        db,
        id_usuario,
    )

    if usuario is None:
        raise UsuarioNoEncontradoError(
            "El usuario indicado no existe."
        )

    cantidad_sesiones = contar_sesiones_vigentes(
        db,
        id_usuario=id_usuario,
        fecha_actual=utc_now(),
    )

    return UsuarioAdministradorDetalleResponse(
        id_usuario=usuario.id_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        estado=usuario.estado,
        fecha_ultimo_acceso=usuario.fecha_ultimo_acceso,
        fecha_creacion=usuario.fecha_creacion,
        fecha_actualizacion=usuario.fecha_actualizacion,
        correos=usuario.correos,
        roles=_obtener_roles_activos(usuario),
        cantidad_sesiones_activas=cantidad_sesiones,
    )


def listar_usuarios_administracion(
    db: Session,
    *,
    pagina: int = 1,
    por_pagina: int = 20,
    estado: str | None = None,
    texto_busqueda: str | None = None,
) -> ListaUsuariosResponse:
    """
    Lista usuarios con filtros y paginación.
    """
    if (
        estado is not None
        and estado not in ESTADOS_USUARIO_VALIDOS
    ):
        raise EstadoUsuarioInvalidoError(
            "El estado de usuario no es válido."
        )

    usuarios, total = listar_usuarios(
        db,
        pagina=pagina,
        por_pagina=por_pagina,
        estado=estado,
        texto_busqueda=texto_busqueda,
    )

    items = [
        UsuarioResumenResponse.model_validate(usuario)
        for usuario in usuarios
    ]

    return ListaUsuariosResponse(
        items=items,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


def cambiar_estado_usuario(
    db: Session,
    *,
    id_usuario: int,
    nuevo_estado: str,
    id_usuario_actor: int,
    motivo: str | None = None,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> UsuarioAdministradorDetalleResponse:
    """
    Cambia el estado de una cuenta desde administración.

    Cuando una cuenta se bloquea o desactiva, se revocan
    todas sus sesiones activas.
    """
    if nuevo_estado not in ESTADOS_USUARIO_VALIDOS:
        raise EstadoUsuarioInvalidoError(
            "El estado de usuario no es válido."
        )

    usuario = obtener_usuario_por_id(
        db,
        id_usuario,
    )

    if usuario is None:
        raise UsuarioNoEncontradoError(
            "El usuario indicado no existe."
        )

    estado_anterior = usuario.estado

    try:
        actualizar_estado_usuario(
            db,
            usuario,
            estado=nuevo_estado,
        )

        sesiones_revocadas = 0

        if nuevo_estado in {
            "bloqueado",
            "inactivo",
        }:
            sesiones_revocadas = revocar_sesiones_usuario(
                db,
                id_usuario=id_usuario,
                fecha_revocacion=utc_now(),
                motivo_revocacion=(
                    f"cuenta_{nuevo_estado}"
                ),
            )

        registrar_accion_simple(
            db,
            id_usuario_actor=id_usuario_actor,
            accion="cambiar_estado_usuario",
            modulo="usuarios",
            entidad="usuario",
            id_entidad=id_usuario,
            detalle={
                "estado_anterior": estado_anterior,
                "estado_nuevo": nuevo_estado,
                "motivo": motivo,
                "sesiones_revocadas": sesiones_revocadas,
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        return obtener_usuario_administracion(
            db,
            id_usuario=id_usuario,
        )

    except Exception:
        db.rollback()
        raise