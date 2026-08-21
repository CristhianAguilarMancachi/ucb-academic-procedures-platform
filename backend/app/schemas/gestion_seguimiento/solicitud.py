from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


EstadoSolicitud = Literal[
    "borrador",
    "pendiente_recepcion",
    "en_revision",
]


# =========================================================
# DATOS DINAMICOS DE LA SOLICITUD
# =========================================================


class SolicitudDatoGuardarRequest(BaseModel):
    id_campo: int = Field(gt=0)

    valor: Any

    @field_validator("valor")
    @classmethod
    def validar_valor_no_nulo(
        cls,
        valor: Any,
    ) -> Any:
        if valor is None:
            raise ValueError(
                "El valor del campo no puede ser nulo."
            )

        return valor


class SolicitudDatoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_solicitud_dato: int
    id_solicitud: int
    id_campo: int

    valor: Any

    fecha_creacion: datetime
    fecha_actualizacion: datetime


# =========================================================
# FACTURAS DE REQUISITOS ECONOMICOS
# =========================================================


class SolicitudFacturaGuardarRequest(BaseModel):
    id_requisito: int = Field(
        gt=0,
    )

    numero_factura: str = Field(
        min_length=1,
        max_length=150,
    )

    @field_validator("numero_factura")
    @classmethod
    def normalizar_numero_factura(
        cls,
        valor: str,
    ) -> str:
        valor_normalizado = valor.strip()

        if not valor_normalizado:
            raise ValueError(
                "El número de factura no puede estar vacío."
            )

        return valor_normalizado


class SolicitudEnviarRequest(BaseModel):
    facturas: list[SolicitudFacturaGuardarRequest] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validar_requisitos_sin_repetir(
        self,
    ) -> "SolicitudEnviarRequest":
        ids_requisitos = [
            factura.id_requisito
            for factura in self.facturas
        ]

        if len(ids_requisitos) != len(set(ids_requisitos)):
            raise ValueError(
                "No puede registrarse más de una factura "
                "para el mismo requisito."
            )

        return self


# =========================================================
# REQUISITOS COPIADOS AL ENVIAR LA SOLICITUD
# =========================================================


class SolicitudRequisitoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_solicitud_requisito: int
    id_solicitud: int

    id_requisito_origen: int | None

    nombre: str
    descripcion: str | None
    obligatorio: bool
    orden: int

    id_requisito_economico_origen: int | None

    concepto_economico: str | None
    monto_economico: Decimal | None
    moneda: str | None
    gestion: int | None
    codigo_concepto_externo: str | None

    numero_factura: str | None

    fecha_creacion: datetime
    fecha_actualizacion: datetime

    @property
    def es_economico(self) -> bool:
        return self.concepto_economico is not None


# =========================================================
# INFORMACION BASICA DEL TRAMITE DENTRO DE UNA SOLICITUD
# =========================================================


class TramiteSolicitudResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_tramite: int
    nombre: str
    descripcion: str | None


# =========================================================
# CREACION Y ACTUALIZACION DE BORRADOR
# =========================================================


class SolicitudCrearRequest(BaseModel):
    id_tramite: int = Field(gt=0)


class SolicitudActualizarRequest(BaseModel):
    datos: list[SolicitudDatoGuardarRequest] | None = None


# =========================================================
# RESPUESTAS
# =========================================================


class SolicitudResumenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_solicitud: int

    id_tramite: int
    estado: EstadoSolicitud

    fecha_creacion: datetime
    fecha_envio: datetime | None
    fecha_actualizacion: datetime

    tramite: TramiteSolicitudResponse


class SolicitudResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_solicitud: int
    id_solicitante: int

    id_tramite: int
    estado: EstadoSolicitud

    fecha_creacion: datetime
    fecha_envio: datetime | None
    fecha_actualizacion: datetime

    tramite: TramiteSolicitudResponse

    datos: list[SolicitudDatoResponse] = Field(
        default_factory=list
    )

    requisitos: list[SolicitudRequisitoResponse] = Field(
        default_factory=list
    )


class ListaSolicitudesResponse(BaseModel):
    items: list[SolicitudResumenResponse]

    total: int = Field(
        ge=0,
    )

    pagina: int = Field(
        ge=1,
    )

    por_pagina: int = Field(
        ge=1,
    )