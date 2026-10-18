
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.gestion_seguimiento.seguimiento import (
    CondicionRequisito,
    TipoFinalizacion,
    TipoIntervencion,
)


# ============================================================
# DATOS GENERALES
# ============================================================

class TramiteBase(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    nombre: str = Field(
        min_length=3,
        max_length=200,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=3000,
    )

    tiempo_estimado: str | None = Field(
        default=None,
        max_length=1000,
    )

    canales_atencion: str | None = Field(
        default=None,
        max_length=2000,
    )

    instrucciones: str | None = Field(
        default=None,
        max_length=5000,
    )

    condiciones: str | None = Field(
        default=None,
        max_length=5000,
    )

    tipo_finalizacion: TipoFinalizacion | None = None

    tipo_intervencion: TipoIntervencion = "ninguna"

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, valor: str) -> str:
        valor = " ".join(valor.split())

        if not any(caracter.isalpha() for caracter in valor):
            raise ValueError(
                "El nombre debe contener al menos una letra."
            )

        return valor


# ============================================================
# CREACIÓN Y ACTUALIZACIÓN
# ============================================================

class TramiteCrearRequest(TramiteBase):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    activo: bool = True
    publicado: bool = False
    permite_solicitudes: bool = False


class TramiteActualizarRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    nombre: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=3000,
    )

    tiempo_estimado: str | None = Field(
        default=None,
        max_length=1000,
    )

    canales_atencion: str | None = Field(
        default=None,
        max_length=2000,
    )

    instrucciones: str | None = Field(
        default=None,
        max_length=5000,
    )

    condiciones: str | None = Field(
        default=None,
        max_length=5000,
    )

    tipo_finalizacion: TipoFinalizacion | None = None

    tipo_intervencion: TipoIntervencion | None = None

    activo: bool | None = None
    publicado: bool | None = None
    permite_solicitudes: bool | None = None

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        valor = " ".join(valor.split())

        if not any(caracter.isalpha() for caracter in valor):
            raise ValueError(
                "El nombre debe contener al menos una letra."
            )

        return valor


# ============================================================
# RESPUESTAS GENERALES
# ============================================================

class TramiteResumenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_tramite: int

    nombre: str
    descripcion: str | None

    tiempo_estimado: str | None = None
    canales_atencion: str | None = None
    instrucciones: str | None = None
    condiciones: str | None = None

    tipo_finalizacion: TipoFinalizacion | None = None
    tipo_intervencion: TipoIntervencion = "ninguna"


class TramiteResponse(TramiteResumenResponse):
    activo: bool
    publicado: bool
    permite_solicitudes: bool

    fecha_creacion: datetime
    fecha_actualizacion: datetime

    cantidad_requisitos_activos: int = 0

    # Compatibilidad temporal con frontend.
    cantidad_etapas_activas: int = 0


# ============================================================
# CATÁLOGO PÚBLICO
# ============================================================

class TramiteCatalogoEconomicoResponse(BaseModel):
    concepto: str
    monto: Decimal
    moneda: str
    gestion: int


class TramiteCatalogoRequisitoResponse(BaseModel):
    id_requisito: int

    nombre: str
    descripcion: str | None

    obligatorio: bool
    orden: int

    requiere_presentacion_fisica: bool = False
    condicion: CondicionRequisito | None = None

    es_economico: bool = False

    informacion_economica: (
        TramiteCatalogoEconomicoResponse | None
    ) = None

    # Compatibilidad temporal.
    es_inicial: bool = True


class TramiteCatalogoCampoResponse(BaseModel):
    id_campo: int

    clave: str
    etiqueta: str
    descripcion: str | None

    tipo_dato: str
    obligatorio: bool
    orden: int

    configuracion: dict[str, Any] | None


class TramiteCatalogoDetalleResponse(BaseModel):
    id_tramite: int

    nombre: str
    descripcion: str | None

    permite_solicitudes: bool

    tiempo_estimado: str | None = None
    canales_atencion: str | None = None
    instrucciones: str | None = None
    condiciones: str | None = None

    tipo_finalizacion: TipoFinalizacion | None = None
    tipo_intervencion: TipoIntervencion = "ninguna"

    requisitos: list[
        TramiteCatalogoRequisitoResponse
    ] = Field(default_factory=list)

    campos: list[
        TramiteCatalogoCampoResponse
    ] = Field(default_factory=list)

    # Compatibilidad hasta actualizar Angular.
    pasos: list[str] = Field(default_factory=list)


# ============================================================
# DETALLE ADMINISTRATIVO
# ============================================================

class TramiteDetalleResponse(TramiteResponse):
    requisitos: list["TramiteRequisitoResponse"] = Field(
        default_factory=list,
    )

    campos: list["TramiteCampoResponse"] = Field(
        default_factory=list,
    )

    # Se retirará tras la actualización del frontend.
    etapas: list["TramiteEtapaResponse"] = Field(
        default_factory=list,
    )


# ============================================================
# LISTADOS
# ============================================================

class ListaTramitesResponse(BaseModel):
    items: list[TramiteResponse]

    total: int = Field(ge=0)
    pagina: int = Field(ge=1)
    por_pagina: int = Field(ge=1, le=100)


class ListaCatalogoTramitesResponse(BaseModel):
    items: list[TramiteResumenResponse]
    total: int = Field(ge=0)


# ============================================================
# REFERENCIAS DE SCHEMAS
# ============================================================

from app.schemas.gestion_seguimiento.tramite_campo import (
    TramiteCampoResponse,
)

from app.schemas.gestion_seguimiento.tramite_requisito import (
    TramiteRequisitoResponse,
)

from app.schemas.gestion_seguimiento.tramite_etapa import (
    TramiteEtapaResponse,
)

TramiteDetalleResponse.model_rebuild()
