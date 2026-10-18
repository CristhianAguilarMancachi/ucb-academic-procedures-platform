
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.gestion_seguimiento.seguimiento import (
    CondicionRequisito,
)


# ============================================================
# REQUISITOS
# ============================================================

class TramiteRequisitoCrearRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    nombre: str = Field(
        min_length=2,
        max_length=200,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=3000,
    )

    obligatorio: bool = True
    orden: int = Field(default=1, gt=0)
    activo: bool = True

    requiere_presentacion_fisica: bool = False
    condicion: CondicionRequisito | None = None

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, valor: str) -> str:
        valor = " ".join(valor.split())

        if not any(caracter.isalpha() for caracter in valor):
            raise ValueError(
                "El nombre debe contener al menos una letra."
            )

        return valor


class TramiteRequisitoActualizarRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    nombre: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=3000,
    )

    obligatorio: bool | None = None
    orden: int | None = Field(default=None, gt=0)
    activo: bool | None = None

    requiere_presentacion_fisica: bool | None = None
    condicion: CondicionRequisito | None = None

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
# CONFIGURACIÓN ECONÓMICA
# ============================================================

class RequisitoEconomicoCrearRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    concepto: str = Field(
        min_length=2,
        max_length=200,
    )

    monto: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    moneda: str = Field(
        default="BOB",
        min_length=3,
        max_length=3,
    )

    gestion: int = Field(
        ge=2000,
        le=2100,
    )

    codigo_concepto_externo: str | None = Field(
        default=None,
        max_length=100,
    )

    activo: bool = True

    @field_validator("concepto")
    @classmethod
    def normalizar_concepto(cls, valor: str) -> str:
        valor = " ".join(valor.split())

        if not any(caracter.isalpha() for caracter in valor):
            raise ValueError(
                "El concepto debe contener al menos una letra."
            )

        return valor

    @field_validator("moneda")
    @classmethod
    def normalizar_moneda(cls, valor: str) -> str:
        valor = valor.strip().upper()

        if not valor.isalpha():
            raise ValueError(
                "La moneda debe utilizar un código "
                "alfabético de tres caracteres."
            )

        return valor

    @field_validator("codigo_concepto_externo")
    @classmethod
    def normalizar_codigo_externo(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        return valor.strip() or None


class RequisitoEconomicoActualizarRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    concepto: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    monto: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    moneda: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )

    gestion: int | None = Field(
        default=None,
        ge=2000,
        le=2100,
    )

    codigo_concepto_externo: str | None = Field(
        default=None,
        max_length=100,
    )

    activo: bool | None = None

    @field_validator("concepto")
    @classmethod
    def normalizar_concepto(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        valor = " ".join(valor.split())

        if not any(caracter.isalpha() for caracter in valor):
            raise ValueError(
                "El concepto debe contener al menos una letra."
            )

        return valor

    @field_validator("moneda")
    @classmethod
    def normalizar_moneda(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        valor = valor.strip().upper()

        if not valor.isalpha():
            raise ValueError(
                "La moneda debe utilizar un código "
                "alfabético de tres caracteres."
            )

        return valor

    @field_validator("codigo_concepto_externo")
    @classmethod
    def normalizar_codigo_externo(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        return valor.strip() or None


# ============================================================
# RESPUESTAS
# ============================================================

class RequisitoEconomicoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_requisito_economico: int
    id_requisito: int

    concepto: str
    monto: Decimal
    moneda: str
    gestion: int
    codigo_concepto_externo: str | None

    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class TramiteRequisitoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_requisito: int
    id_tramite: int

    nombre: str
    descripcion: str | None
    obligatorio: bool
    orden: int
    activo: bool

    requiere_presentacion_fisica: bool
    condicion: CondicionRequisito | None

    fecha_creacion: datetime
    fecha_actualizacion: datetime

    configuraciones_economicas: list[
        RequisitoEconomicoResponse
    ] = Field(default_factory=list)

    # Compatibilidad temporal con Angular.
    # No forma parte de las nuevas operaciones.
    id_etapa: int | None = None
