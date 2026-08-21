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


class TramiteBase(BaseModel):
    """
    Información general reutilizable de un trámite académico.
    """

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

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, value: str) -> str:
        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El nombre debe contener al menos una letra."
            )

        return value


class TramiteCrearRequest(TramiteBase):
    """
    Datos requeridos para registrar un trámite en el catálogo.

    Por seguridad, un trámite nuevo no se publica ni se habilita
    para solicitudes automáticamente.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    activo: bool = True
    publicado: bool = False
    permite_solicitudes: bool = False


class TramiteActualizarRequest(BaseModel):
    """
    Permite modificar la configuración general de un trámite.
    """

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

    activo: bool | None = None
    publicado: bool | None = None
    permite_solicitudes: bool | None = None

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El nombre debe contener al menos una letra."
            )

        return value


# ============================================================
# RESPUESTAS GENERALES
# ============================================================


class TramiteResumenResponse(BaseModel):
    """
    Información resumida utilizada para mostrar el catálogo.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_tramite: int
    nombre: str
    descripcion: str | None


class TramiteResponse(TramiteResumenResponse):
    """
    Información administrativa completa de un trámite.
    """

    activo: bool
    publicado: bool
    permite_solicitudes: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime


# ============================================================
# DETALLE PÚBLICO DEL CATÁLOGO
# ============================================================


class TramiteCatalogoEconomicoResponse(BaseModel):
    """
    Información económica vigente que puede mostrarse
    al solicitante.
    """

    concepto: str
    monto: Decimal
    moneda: str
    gestion: int


class TramiteCatalogoRequisitoResponse(BaseModel):
    """
    Requisito activo visible para el solicitante.
    """

    id_requisito: int

    nombre: str
    descripcion: str | None

    obligatorio: bool
    orden: int

    es_economico: bool = False

    informacion_economica: (
        TramiteCatalogoEconomicoResponse | None
    ) = None


class TramiteCatalogoCampoResponse(BaseModel):
    """
    Campo configurable que deberá completar el solicitante
    cuando corresponda.
    """

    id_campo: int

    clave: str
    etiqueta: str
    descripcion: str | None

    tipo_dato: str
    obligatorio: bool
    orden: int

    configuracion: dict[str, Any] | None


class TramiteCatalogoDetalleResponse(BaseModel):
    """
    Detalle visible de un trámite publicado.

    No expone etapas, unidades ni configuraciones internas
    del proceso administrativo.
    """

    id_tramite: int

    nombre: str
    descripcion: str | None

    permite_solicitudes: bool

    requisitos: list[
        TramiteCatalogoRequisitoResponse
    ] = Field(
        default_factory=list,
    )

    campos: list[
        TramiteCatalogoCampoResponse
    ] = Field(
        default_factory=list,
    )


# ============================================================
# DETALLE ADMINISTRATIVO
# ============================================================


class TramiteDetalleResponse(TramiteResponse):
    """
    Configuración completa de un trámite.

    Incluye requisitos, campos configurables y, cuando sean
    institucionalmente definidos, sus etapas.
    """

    requisitos: list["TramiteRequisitoResponse"] = Field(
        default_factory=list,
    )

    campos: list["TramiteCampoResponse"] = Field(
        default_factory=list,
    )

    etapas: list["TramiteEtapaResponse"] = Field(
        default_factory=list,
    )


class ListaTramitesResponse(BaseModel):
    """
    Respuesta paginada para administración de trámites.
    """

    items: list[TramiteResponse]
    total: int = Field(ge=0)
    pagina: int = Field(ge=1)
    por_pagina: int = Field(ge=1, le=100)


class ListaCatalogoTramitesResponse(BaseModel):
    """
    Catálogo visible para usuarios del sistema.

    Solo debe contener trámites que el servicio haya validado
    previamente como activos y publicados.
    """

    items: list[TramiteResumenResponse]
    total: int = Field(ge=0)


from app.schemas.gestion_seguimiento.tramite_campo import (
    TramiteCampoResponse,
)
from app.schemas.gestion_seguimiento.tramite_etapa import (
    TramiteEtapaResponse,
)
from app.schemas.gestion_seguimiento.tramite_requisito import (
    TramiteRequisitoResponse,
)

TramiteDetalleResponse.model_rebuild()