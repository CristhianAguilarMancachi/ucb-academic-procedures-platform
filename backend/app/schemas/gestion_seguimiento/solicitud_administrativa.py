from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


EstadoSolicitudAdministrativa = Literal[
    "pendiente_recepcion",
    "en_revision",
]

EstadoVerificacionRequisito = Literal[
    "pendiente",
    "cumple",
    "no_cumple",
]


class SolicitudAdministrativaResumenResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id_solicitud: int

    id_solicitante: int

    id_tramite: int

    nombre_tramite: str

    estado: str

    fecha_creacion: datetime

    fecha_envio: datetime | None


class ListaSolicitudesAdministrativasResponse(BaseModel):
    items: list[SolicitudAdministrativaResumenResponse]

    total: int

    pagina: int

    limite: int


class SolicitudDatoAdministrativoResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id_solicitud_dato: int

    id_campo: int

    valor: Any


class SolicitudRequisitoAdministrativoResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id_solicitud_requisito: int

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

    estado_verificacion: EstadoVerificacionRequisito

    id_usuario_verificador: int | None

    fecha_verificacion: datetime | None

    detalle_verificacion: str | None

    @property
    def es_economico(self) -> bool:
        return self.id_requisito_economico_origen is not None


class SolicitudRecepcionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id_recepcion: int

    id_solicitud: int

    id_usuario_receptor: int

    fecha_recepcion: datetime


class SolicitudAdministrativaDetalleResponse(BaseModel):
    id_solicitud: int

    id_solicitante: int

    id_tramite: int

    nombre_tramite: str

    estado: str

    fecha_creacion: datetime

    fecha_envio: datetime | None

    datos: list[SolicitudDatoAdministrativoResponse]

    requisitos: list[
        SolicitudRequisitoAdministrativoResponse
    ]

    recepcion: SolicitudRecepcionResponse | None


class RequisitoVerificarRequest(BaseModel):
    estado: Literal[
        "cumple",
        "no_cumple",
    ]

    detalle: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("detalle")
    @classmethod
    def normalizar_detalle(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        valor_normalizado = valor.strip()

        if not valor_normalizado:
            return None

        return valor_normalizado


class RequisitoVerificacionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id_solicitud_requisito: int

    estado_verificacion: EstadoVerificacionRequisito

    id_usuario_verificador: int | None

    fecha_verificacion: datetime | None

    detalle_verificacion: str | None