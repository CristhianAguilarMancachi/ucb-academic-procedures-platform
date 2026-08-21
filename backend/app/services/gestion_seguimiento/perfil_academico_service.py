from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.gestion_seguimiento import (
    perfil_academico_repository,
)
from app.repositories.usuario_repository import (
    obtener_usuario_por_id,
)
from app.schemas.gestion_seguimiento.perfil_academico import (
    PerfilAcademicoActualizarRequest,
    PerfilAcademicoResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
)


class PerfilAcademicoServiceError(Exception):
    """Error base del servicio de perfil académico."""


class PerfilAcademicoNoEncontradoError(
    PerfilAcademicoServiceError
):
    """El usuario todavía no tiene perfil académico."""


class UsuarioNoEncontradoError(
    PerfilAcademicoServiceError
):
    """La cuenta de usuario no existe."""


class ActualizacionPerfilAcademicoVaciaError(
    PerfilAcademicoServiceError
):
    """No se proporcionaron campos para actualizar."""


def obtener_perfil_academico_usuario(
    db: Session,
    *,
    id_usuario: int,
) -> PerfilAcademicoResponse:
    """
    Obtiene el perfil académico asociado al usuario.
    """
    perfil = (
        perfil_academico_repository
        .obtener_perfil_por_usuario(
            db,
            id_usuario,
        )
    )

    if perfil is None:
        raise PerfilAcademicoNoEncontradoError(
            "El usuario todavía no tiene un perfil académico."
        )

    return PerfilAcademicoResponse.model_validate(
        perfil
    )


def actualizar_perfil_academico_usuario(
    db: Session,
    *,
    id_usuario: int,
    datos: PerfilAcademicoActualizarRequest,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> PerfilAcademicoResponse:
    """
    Crea o actualiza el perfil académico del usuario.

    Los campos no enviados permanecen sin cambios.
    Los campos enviados explícitamente como null se limpian.
    """
    if not datos.model_fields_set:
        raise ActualizacionPerfilAcademicoVaciaError(
            "Debe indicar al menos un campo para actualizar."
        )

    usuario = obtener_usuario_por_id(
        db,
        id_usuario,
    )

    if usuario is None:
        raise UsuarioNoEncontradoError(
            "El usuario indicado no existe."
        )

    cambios = {
        campo: getattr(
            datos,
            campo,
        )
        for campo in datos.model_fields_set
    }

    try:
        perfil = (
            perfil_academico_repository
            .obtener_perfil_por_usuario(
                db,
                id_usuario,
            )
        )

        if perfil is None:
            perfil = (
                perfil_academico_repository
                .crear_perfil(
                    db,
                    id_usuario=id_usuario,
                    **cambios,
                )
            )

            accion = "crear_perfil_academico"

        else:
            perfil = (
                perfil_academico_repository
                .actualizar_perfil(
                    db,
                    perfil,
                    cambios=cambios,
                )
            )

            accion = "actualizar_perfil_academico"

        registrar_accion_simple(
            db,
            accion=accion,
            modulo="gestion_seguimiento",
            id_usuario_actor=id_usuario,
            entidad="perfil_academico",
            id_entidad=str(
                perfil.id_perfil
            ),
            exitoso=True,
            detalle={
                "campos_actualizados": sorted(
                    cambios.keys()
                ),
            },
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()
        db.refresh(perfil)

        return PerfilAcademicoResponse.model_validate(
            perfil
        )

    except Exception:
        db.rollback()
        raise