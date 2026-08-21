from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


TipoDatoCampo = Literal[
    "texto",
    "texto_largo",
    "entero",
    "decimal",
    "fecha",
    "booleano",
    "seleccion",
]


class TramiteCampoBase(BaseModel):
    """
    Configuración reutilizable de un campo particular de un trámite.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    clave: str = Field(
        min_length=2,
        max_length=80,
    )

    etiqueta: str = Field(
        min_length=2,
        max_length=150,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=2000,
    )

    tipo_dato: TipoDatoCampo

    obligatorio: bool = False

    orden: int = Field(
        default=1,
        gt=0,
    )

    configuracion: dict[str, Any] | None = None

    activo: bool = True

    @field_validator("clave")
    @classmethod
    def validar_clave(cls, value: str) -> str:
        value = value.strip().lower()

        if not re.fullmatch(
            r"[a-z][a-z0-9_]*",
            value,
        ):
            raise ValueError(
                "La clave debe comenzar con una letra y "
                "solo puede contener letras minúsculas, "
                "números y guiones bajos."
            )

        return value

    @field_validator("etiqueta")
    @classmethod
    def normalizar_etiqueta(cls, value: str) -> str:
        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "La etiqueta debe contener al menos una letra."
            )

        return value

    @model_validator(mode="after")
    def validar_configuracion(self) -> "TramiteCampoBase":
        if self.tipo_dato != "seleccion":
            return self

        if self.configuracion is None:
            raise ValueError(
                "Los campos de tipo 'seleccion' deben incluir "
                "una configuración con sus opciones."
            )

        opciones = self.configuracion.get("opciones")

        if not isinstance(opciones, list) or not opciones:
            raise ValueError(
                "La configuración de un campo de selección debe "
                "contener una lista no vacía llamada 'opciones'."
            )

        opciones_normalizadas: list[str] = []

        for opcion in opciones:
            if not isinstance(opcion, str):
                raise ValueError(
                    "Cada opción debe ser una cadena de texto."
                )

            opcion = " ".join(opcion.split())

            if not opcion:
                raise ValueError(
                    "Las opciones no pueden estar vacías."
                )

            opciones_normalizadas.append(opcion)

        if len(set(opciones_normalizadas)) != len(
            opciones_normalizadas
        ):
            raise ValueError(
                "Las opciones de un campo de selección "
                "no pueden estar duplicadas."
            )

        self.configuracion["opciones"] = opciones_normalizadas

        return self


class TramiteCampoCrearRequest(TramiteCampoBase):
    """
    Registra un campo configurable dentro de un trámite.

    id_tramite se obtiene mediante la ruta del endpoint.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )


class TramiteCampoActualizarRequest(BaseModel):
    """
    Permite modificar un campo configurable existente.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    clave: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
    )

    etiqueta: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=2000,
    )

    tipo_dato: TipoDatoCampo | None = None

    obligatorio: bool | None = None

    orden: int | None = Field(
        default=None,
        gt=0,
    )

    configuracion: dict[str, Any] | None = None

    activo: bool | None = None

    @field_validator("clave")
    @classmethod
    def validar_clave(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip().lower()

        if not re.fullmatch(
            r"[a-z][a-z0-9_]*",
            value,
        ):
            raise ValueError(
                "La clave debe comenzar con una letra y "
                "solo puede contener letras minúsculas, "
                "números y guiones bajos."
            )

        return value

    @field_validator("etiqueta")
    @classmethod
    def normalizar_etiqueta(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = " ".join(value.split())

        if not any(character.isalpha() for character in value):
            raise ValueError(
                "La etiqueta debe contener al menos una letra."
            )

        return value


class TramiteCampoResponse(BaseModel):
    """
    Información completa de un campo configurable de trámite.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_campo: int
    id_tramite: int
    clave: str
    etiqueta: str
    descripcion: str | None
    tipo_dato: TipoDatoCampo
    obligatorio: bool
    orden: int
    configuracion: dict[str, Any] | None
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime