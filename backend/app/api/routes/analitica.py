from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from app.core.dependencies import DatabaseSession, PersonalAdministrativoActual
from app.schemas.analitica import AnaliticaResponse, FiltrosAnalitica, PeriodoAnalitica
from app.services.analitica_service import obtener_analitica, TramiteAnaliticaNoEncontrado


router = APIRouter(prefix='/admin/analitica', tags=['Analítica e indicadores'])


@router.get('', response_model=AnaliticaResponse)
def consultar_analitica(
    db: DatabaseSession,
    usuario: PersonalAdministrativoActual,
    periodo: PeriodoAnalitica = Query(default='30_dias'),
    id_tramite: int | None = Query(default=None, gt=0),
) -> AnaliticaResponse:
    # Mismo ámbito global que la bandeja administrativa existente.
    try:
        return obtener_analitica(db, FiltrosAnalitica(periodo=periodo, id_tramite=id_tramite))
    except TramiteAnaliticaNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail='No se pudo consultar la analítica. Intenta nuevamente.') from exc
