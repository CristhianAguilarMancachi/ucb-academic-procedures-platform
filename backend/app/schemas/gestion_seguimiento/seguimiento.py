from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator

TipoFinalizacion = Literal['entrega', 'resultado_registrado', 'externo']


class CondicionDato(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)
    origen: Literal['solicitud_dato']
    clave: str = Field(min_length=1, max_length=100)
    operador: Literal['igual']
    valor: StrictStr | StrictInt | StrictFloat | StrictBool


class CondicionPerfil(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    origen: Literal['perfil_academico']
    campo: Literal['codigo_estudiante', 'sede', 'carrera_programa', 'nivel_academico', 'documento_identidad']
    operador: Literal['igual']
    valor: str = Field(min_length=1, max_length=200)


CondicionRequisito = Annotated[CondicionDato | CondicionPerfil, Field(discriminator='origen')]


class SolicitudEtapaPublicaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_solicitud_etapa: int
    nombre: str
    descripcion: str | None
    orden: int
    estado: Literal['pendiente', 'en_curso', 'completada']
    fecha_inicio: datetime | None
    fecha_finalizacion: datetime | None


class SolicitudEtapaResponse(SolicitudEtapaPublicaResponse):
    id_etapa_origen: int | None
    id_unidad: int | None
    es_inicial: bool
    es_final: bool
    visible_solicitante: bool
    id_usuario_inicio: int | None
    id_usuario_finalizacion: int | None


class HistorialPublicoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_historial: int
    evento: str
    detalle: str
    fecha_evento: datetime


class HistorialResponse(HistorialPublicoResponse):
    id_solicitud_etapa: int | None = None
    id_solicitud_requisito: int | None = None
    id_usuario_actor: int | None
    visible_solicitante: bool


class ObservacionCrearRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id_solicitud_etapa: int | None = Field(default=None, gt=0)
    id_solicitud_requisito: int | None = Field(default=None, gt=0)
    detalle: str = Field(min_length=1, max_length=3000)
    correccion_requerida: str = Field(min_length=1, max_length=3000)
    canal_subsanacion: str | None = Field(default=None, max_length=1000)


class ObservacionPublicaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_observacion: int
    id_solicitud_requisito: int | None
    detalle: str
    correccion_requerida: str
    canal_subsanacion: str | None
    estado: Literal['pendiente', 'resuelta']
    fecha_observacion: datetime
    fecha_resolucion: datetime | None


class ObservacionResponse(ObservacionPublicaResponse):
    id_solicitud_etapa: int | None
    id_usuario_observador: int
    id_usuario_resolucion: int | None


class MotivoRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    motivo: str = Field(min_length=1, max_length=2000)


class FacturaRegistrarRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    numero_factura: str = Field(min_length=1, max_length=150)


class ResultadoRegistrarRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    detalle: str | None = Field(default=None, max_length=3000)
    # Solo para solicitudes anteriores que carecen de snapshot de finalización.
    tipo_finalizacion: TipoFinalizacion | None = None


class ResultadoPublicoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tipo_finalizacion: TipoFinalizacion
    detalle: str | None
    fecha_registro: datetime


class ResultadoResponse(ResultadoPublicoResponse):
    id_resultado: int
    id_usuario_registro: int


class EntregaRegistrarRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    receptor: Literal['titular', 'tercero']
    nombre_receptor: str | None = Field(default=None, min_length=2, max_length=200)
    documento_identidad: str | None = Field(default=None, min_length=1, max_length=50)
    detalle: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validar_tercero(self):
        if self.receptor == 'tercero' and not self.nombre_receptor:
            raise ValueError('Debe indicar el nombre de quien recoge.')
        return self


class EntregaResponse(EntregaRegistrarRequest):
    model_config = ConfigDict(from_attributes=True)
    id_entrega: int
    id_usuario_entrega: int
    fecha_entrega: datetime


class SeguimientoResponse(BaseModel):
    id_solicitud: int
    identificador: str
    nombre_tramite: str
    estado: str
    etapa_actual: SolicitudEtapaPublicaResponse | None
    etapas: list[SolicitudEtapaPublicaResponse]
    avance_porcentaje: int
    observaciones: list[ObservacionPublicaResponse]
    observaciones_pendientes: int
    historial: list[HistorialPublicoResponse]
    resultado: ResultadoPublicoResponse | None
    fecha_entrega: datetime | None
