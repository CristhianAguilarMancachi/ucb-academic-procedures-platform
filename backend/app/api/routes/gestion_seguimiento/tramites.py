from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.core.dependencies import (
    DatabaseSession,
)
from app.schemas.gestion_seguimiento.tramite import (
    ListaCatalogoTramitesResponse,
    TramiteCatalogoDetalleResponse,
)
from app.services.gestion_seguimiento.tramite_service import (
    TramiteNoEncontradoError,
    obtener_catalogo_publicado,
    obtener_tramite_catalogo_publico,
)


router = APIRouter(
    prefix="/tramites",
    tags=["Trámites"],
)


@router.get(
    "",
    response_model=ListaCatalogoTramitesResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_catalogo(
    db: DatabaseSession,
) -> ListaCatalogoTramitesResponse:
    """
    Devuelve los trámites visibles en el catálogo.

    Únicamente se muestran registros activos y publicados.
    Las configuraciones administrativas internas no se exponen
    mediante este endpoint.
    """
    return obtener_catalogo_publicado(
        db
    )


@router.get(
    "/{id_tramite}",
    response_model=TramiteCatalogoDetalleResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_detalle_tramite(
    id_tramite: int,
    db: DatabaseSession,
) -> TramiteCatalogoDetalleResponse:
    """
    Devuelve el detalle visible de un trámite publicado.

    Incluye requisitos, información económica vigente
    y campos configurables.

    No expone etapas ni unidades administrativas internas.
    """
    try:
        return obtener_tramite_catalogo_publico(
            db,
            id_tramite=id_tramite,
        )

    except TramiteNoEncontradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc