from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from app.schemas.gestion_seguimiento.seguimiento import CondicionRequisito

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class TramiteRequisitoCrearRequest(BaseModel):
    id_etapa: int | None = Field(default=None, gt=0)
    requiere_presentacion_fisica: bool = False
    condicion: CondicionRequisito | None = None

    """
    Datos requeridos para agregar un requisito a un trámite.

    El trámite se determina mediante la ruta del endpoint,
    por lo que id_tramite no se recibe en el cuerpo.
    """

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

    orden: int = Field(
        default=1,
        gt=0,
    )

    activo: bool = True

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, value: str) -> str:
        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El nombre debe contener al menos una letra."
            )

        return value


class TramiteRequisitoActualizarRequest(BaseModel):
    id_etapa: int | None = Field(default=None, gt=0)
    requiere_presentacion_fisica: bool | None = None
    condicion: CondicionRequisito | None = None

    """
    Permite modificar la configuración de un requisito.
    """

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

    orden: int | None = Field(
        default=None,
        gt=0,
    )

    activo: bool | None = None

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


class RequisitoEconomicoCrearRequest(BaseModel):
    """
    Configuración económica asociada a un requisito.

    No representa un pago realizado por un usuario.
    """

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
    def normalizar_concepto(cls, value: str) -> str:
        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El concepto debe contener al menos una letra."
            )

        return value

    @field_validator("moneda")
    @classmethod
    def normalizar_moneda(cls, value: str) -> str:
        value = value.strip().upper()

        if not value.isalpha():
            raise ValueError(
                "La moneda debe utilizar un código alfabético "
                "de tres caracteres."
            )

        return value

    @field_validator("codigo_concepto_externo")
    @classmethod
    def normalizar_codigo_externo(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None


class RequisitoEconomicoActualizarRequest(BaseModel):
    """
    Permite modificar una configuración económica existente.
    """

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
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "El concepto debe contener al menos una letra."
            )

        return value

    @field_validator("moneda")
    @classmethod
    def normalizar_moneda(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip().upper()

        if not value.isalpha():
            raise ValueError(
                "La moneda debe utilizar un código alfabético "
                "de tres caracteres."
            )

        return value

    @field_validator("codigo_concepto_externo")
    @classmethod
    def normalizar_codigo_externo(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None


class RequisitoEconomicoResponse(BaseModel):
    """
    Información económica configurada para un requisito.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

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
    id_etapa: int | None
    requiere_presentacion_fisica: bool
    condicion: CondicionRequisito | None

    """
    Información completa de un requisito de trámite.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_requisito: int
    id_tramite: int
    nombre: str
    descripcion: str | None
    obligatorio: bool
    orden: int
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    configuraciones_economicas: list[
        RequisitoEconomicoResponse
    ] = Field(
        default_factory=list,
    )