from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class TramiteEtapaCrearRequest(BaseModel):
    visible_solicitante: bool = False

    """
    Configuración de una etapa perteneciente a un trámite.

    La infraestructura queda disponible para registrar etapas
    cuando el proceso administrativo correspondiente haya sido
    confirmado institucionalmente.

    id_tramite se obtiene desde la ruta del endpoint.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    id_unidad: int | None = Field(
        default=None,
        gt=0,
    )

    nombre: str = Field(
        min_length=2,
        max_length=150,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=3000,
    )

    orden: int = Field(
        gt=0,
    )

    es_inicial: bool = False

    es_final: bool = False

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


class TramiteEtapaActualizarRequest(BaseModel):
    visible_solicitante: bool | None = None

    """
    Permite modificar una etapa previamente configurada.

    No se permite cambiar id_tramite desde este schema.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    id_unidad: int | None = Field(
        default=None,
        gt=0,
    )

    nombre: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=3000,
    )

    orden: int | None = Field(
        default=None,
        gt=0,
    )

    es_inicial: bool | None = None

    es_final: bool | None = None

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


class TramiteEtapaResponse(BaseModel):
    visible_solicitante: bool

    """
    Información de una etapa configurada para un trámite.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_etapa: int
    id_tramite: int
    id_unidad: int | None

    nombre: str
    descripcion: str | None

    orden: int

    es_inicial: bool
    es_final: bool

    activo: bool

    fecha_creacion: datetime
    fecha_actualizacion: datetime

class EtapasOrdenRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=1000)
