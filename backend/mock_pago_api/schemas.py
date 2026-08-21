from __future__ import annotations

from decimal import Decimal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class FacturaValidarRequest(BaseModel):
    codigo: str = Field(
        min_length=1,
        max_length=100,
    )

    numero_factura: str = Field(
        min_length=1,
        max_length=150,
    )

    @field_validator(
        "codigo",
        "numero_factura",
    )
    @classmethod
    def normalizar_texto(
        cls,
        valor: str,
    ) -> str:
        valor_limpio = valor.strip()

        if not valor_limpio:
            raise ValueError(
                "El valor no puede estar vacío."
            )

        return valor_limpio


class FacturaValidarResponse(BaseModel):
    encontrada: bool

    numero_factura: str

    codigo: str | None = None

    monto: Decimal | None = None

    moneda: str | None = None

    estado_factura: str | None = None

    utilizada: bool | None = None

    mensaje: str | None = None