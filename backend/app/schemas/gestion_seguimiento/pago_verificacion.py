from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


EstadoPagoVerificacion = Literal[
    "verificado",
    "no_verificado",
    "error",
]


class PagoApiValidarRequest(BaseModel):
    """
    Contrato normalizado que nuestro cliente envía a la API
    externa de pagos/facturación.
    """

    codigo: str = Field(
        min_length=1,
        max_length=100,
    )

    numero_factura: str = Field(
        min_length=1,
        max_length=150,
    )

    @field_validator("codigo", "numero_factura")
    @classmethod
    def normalizar_texto(cls, valor: str) -> str:
        valor_normalizado = valor.strip()

        if not valor_normalizado:
            raise ValueError(
                "El valor no puede estar vacío."
            )

        return valor_normalizado


class PagoApiRespuesta(BaseModel):
    """
    Respuesta normalizada de la API externa.

    El mock utilizará este contrato directamente.

    Si la API institucional real utiliza otros nombres,
    pago_api_client.py será responsable de traducirlos a
    esta estructura.
    """

    encontrada: bool

    numero_factura: str

    codigo: str | None = None

    monto: Decimal | None = None

    moneda: str | None = None

    estado_factura: str | None = None

    utilizada: bool | None = None

    mensaje: str | None = None

    @field_validator(
        "numero_factura",
        "codigo",
        "moneda",
        "estado_factura",
        "mensaje",
        mode="before",
    )
    @classmethod
    def normalizar_textos_opcionales(
        cls,
        valor: Any,
    ) -> Any:
        if valor is None:
            return None

        if isinstance(valor, str):
            valor = valor.strip()

        return valor


class PagoVerificacionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id_verificacion_pago: int

    id_solicitud_requisito: int

    numero_factura_consultado: str

    codigo_concepto_consultado: str

    codigo_concepto_reportado: str | None

    estado_factura_reportado: str | None

    monto_reportado: Decimal | None

    moneda_reportada: str | None

    estado: EstadoPagoVerificacion

    fecha_verificacion: datetime


class PagoVerificacionResultadoResponse(
    PagoVerificacionResponse
):
    """
    Respuesta utilizada por el endpoint administrativo.

    Además del registro persistido, proporciona una explicación
    breve del resultado de la operación.
    """

    mensaje: str