from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VigenciaDocumentoRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    vigente_desde: date
    vigente_hasta: date | None = None

    @model_validator(mode="after")
    def validar_periodo(self) -> Self:
        if self.vigente_hasta is not None and self.vigente_hasta < self.vigente_desde:
            raise ValueError("La fecha final no puede ser anterior al inicio de vigencia.")
        return self


class DocumentoCrearRequest(VigenciaDocumentoRequest):
    titulo: str = Field(min_length=3, max_length=255)
    unidad_origen: str = Field(min_length=3, max_length=150)
    descripcion: str | None = Field(default=None, max_length=5000)
    estado: Literal["activo", "inactivo"] = "activo"


class VersionCrearRequest(VigenciaDocumentoRequest):
    observacion: str | None = Field(default=None, max_length=5000)


class DocumentoEstadoRequest(BaseModel):
    estado: Literal["activo", "inactivo"]


class VersionDocumentoResponse(BaseModel):
    id_version_documento: int
    numero_version: str
    estado: str
    fecha_version: datetime
    vigente_desde: date | None
    vigente_hasta: date | None
    desde_efectivo: date
    vigente: bool
    cantidad_chunks: int
    descargable: bool
    observacion: str | None


class DocumentoResponse(BaseModel):
    id_documento_institucional: int
    titulo: str
    unidad_origen: str
    descripcion: str | None
    estado: str
    fecha_carga: datetime
    fecha_actualizacion: datetime
    id_version_actual: int | None
    version_actual: VersionDocumentoResponse | None
    utilizable_rag: bool


class DocumentoDetalleResponse(DocumentoResponse):
    versiones: list[VersionDocumentoResponse]


class ListaDocumentosResponse(BaseModel):
    items: list[DocumentoResponse]
    total: int
    pagina: int
    por_pagina: int
