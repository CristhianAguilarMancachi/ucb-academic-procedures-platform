from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
)

from app.core.dependencies import (
    DatabaseSession,
    SolicitanteActual,
)
from app.schemas.gestion_seguimiento.perfil_academico import (
    PerfilAcademicoActualizarRequest,
    PerfilAcademicoResponse,
)
from app.services.gestion_seguimiento.perfil_academico_service import (
    ActualizacionPerfilAcademicoVaciaError,
    PerfilAcademicoNoEncontradoError,
    UsuarioNoEncontradoError,
    actualizar_perfil_academico_usuario,
    obtener_perfil_academico_usuario,
)


router = APIRouter(
    prefix="/users/me/perfil-academico",
    tags=["Perfil académico"],
)


def _obtener_direccion_ip(
    request: Request,
) -> str | None:
    if request.client is None:
        return None

    return request.client.host


@router.get(
    "",
    response_model=PerfilAcademicoResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_perfil_academico(
    db: DatabaseSession,
    usuario: SolicitanteActual,
) -> PerfilAcademicoResponse:
    """
    Devuelve el perfil académico del usuario autenticado.
    """
    try:
        return obtener_perfil_academico_usuario(
            db,
            id_usuario=usuario.id_usuario,
        )

    except PerfilAcademicoNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "",
    response_model=PerfilAcademicoResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_perfil_academico(
    datos: PerfilAcademicoActualizarRequest,
    request: Request,
    db: DatabaseSession,
    usuario: SolicitanteActual,
) -> PerfilAcademicoResponse:
    """
    Crea o actualiza el perfil académico
    del usuario autenticado.
    """
    try:
        return actualizar_perfil_academico_usuario(
            db,
            id_usuario=usuario.id_usuario,
            datos=datos,
            direccion_ip=_obtener_direccion_ip(
                request
            ),
            user_agent=request.headers.get(
                "user-agent"
            ),
        )

    except ActualizacionPerfilAcademicoVaciaError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except UsuarioNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc