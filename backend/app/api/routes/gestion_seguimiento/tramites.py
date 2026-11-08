from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.core.dependencies import (
    DatabaseSession,
    SolicitanteActual,
)

from pydantic import BaseModel, Field

from app.schemas.gestion_seguimiento.solicitud import (
    SolicitudDatoGuardarRequest,
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


class PreparacionTramiteRequest(BaseModel):
    """Datos para consultar requisitos sin registrar solicitudes."""

    datos: list[SolicitudDatoGuardarRequest] = Field(
        default_factory=list,
    )


@router.post(
    "/{id_tramite}/preparacion",
    response_model=TramiteCatalogoDetalleResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_preparacion_sin_borrador(
    id_tramite: int,
    datos: PreparacionTramiteRequest,
    db: DatabaseSession,
    usuario: SolicitanteActual,
) -> TramiteCatalogoDetalleResponse:
    """
    Consulta requisitos aplicables sin crear una solicitud.

    Valida los valores recibidos y utiliza el perfil académico
    del solicitante para resolver condiciones.
    """
    from types import SimpleNamespace

    from app.repositories.gestion_seguimiento import (
        tramite_repository,
    )
    from app.services.gestion_seguimiento.configuracion_flujo_service import (
        requisitos_aplicables_sin_solicitud,
    )
    from app.services.gestion_seguimiento.solicitud_service import (
        SolicitudServiceError,
        _normalizar_datos_formulario,
        _obtener_tramite_habilitado,
    )
    from app.services.gestion_seguimiento.seguimiento_service import (
        SeguimientoError,
    )

    try:
        _obtener_tramite_habilitado(db, id_tramite)

        catalogo = obtener_tramite_catalogo_publico(
            db,
            id_tramite=id_tramite,
        )

        campos = tramite_repository.listar_campos_tramite(
            db,
            id_tramite,
            solo_activos=True,
        )

        requisitos = tramite_repository.listar_requisitos_tramite(
            db,
            id_tramite,
            solo_activos=True,
        )

        valores = _normalizar_datos_formulario(
            db,
            id_tramite=id_tramite,
            datos=datos.datos,
        )

        faltantes = [
            campo.etiqueta
            for campo in campos
            if campo.obligatorio and campo.id_campo not in valores
        ]

        if faltantes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Faltan campos obligatorios: "
                    + ", ".join(faltantes)
                    + "."
                ),
            )

        datos_normalizados = [
            SimpleNamespace(id_campo=id_campo, valor=valor)
            for id_campo, valor in valores.items()
        ]

        aplicables = requisitos_aplicables_sin_solicitud(
            db,
            id_solicitante=usuario.id_usuario,
            requisitos=requisitos,
            campos=campos,
            datos=datos_normalizados,
        )

        ids_aplicables = {
            requisito.id_requisito
            for requisito in aplicables
        }

        catalogo.requisitos = [
            requisito
            for requisito in catalogo.requisitos
            if requisito.id_requisito in ids_aplicables
        ]

        return catalogo

    except HTTPException:
        raise

    except SeguimientoError as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 400),
            detail=str(exc),
        ) from exc

    except SolicitudServiceError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


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