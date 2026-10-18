from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


PeriodoAnalitica = Literal['30_dias', '90_dias', '12_meses']


class FiltrosAnalitica(BaseModel):
    periodo: PeriodoAnalitica = '30_dias'
    id_tramite: int | None = Field(default=None, gt=0)


class TramiteAnalitica(BaseModel):
    id_tramite: int
    nombre: str


class DemandaTramite(TramiteAnalitica):
    cantidad: int


class IndicadoresAnalitica(BaseModel):
    solicitudes_recibidas: int
    solicitudes_concluidas: int | None
    tiempo_mediano_dias: float | None
    consultas_rag: int


class EvolucionSolicitudes(BaseModel):
    periodo: date
    recibidas: int
    concluidas: int | None


class EvolucionRag(BaseModel):
    periodo: date
    consultas: int


class AnaliticaResponse(BaseModel):
    filtros: FiltrosAnalitica
    desde: datetime
    hasta: datetime
    zona_horaria: str
    agrupacion: Literal['semana', 'mes']
    indicadores: IndicadoresAnalitica
    evolucion_solicitudes: list[EvolucionSolicitudes]
    top_tramites: list[DemandaTramite]
    evolucion_rag: list[EvolucionRag]
    tramites: list[TramiteAnalitica]
    clasificacion_rag_disponible: bool = False
    limitaciones: list[str]
