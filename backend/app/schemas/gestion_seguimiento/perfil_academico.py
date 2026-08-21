from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PerfilAcademicoActualizarRequest(BaseModel):
    codigo_estudiante: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    sede: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    carrera_programa: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    nivel_academico: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    documento_identidad: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
    )

    @field_validator(
        "codigo_estudiante",
        "sede",
        "carrera_programa",
        "nivel_academico",
        "documento_identidad",
        mode="before",
    )
    @classmethod
    def limpiar_campos_opcionales(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        if not isinstance(valor, str):
            return valor

        valor_limpio = valor.strip()

        if not valor_limpio:
            return None

        return valor_limpio


class PerfilAcademicoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_perfil: int
    id_usuario: int

    codigo_estudiante: str | None
    sede: str | None
    carrera_programa: str | None
    nivel_academico: str | None
    documento_identidad: str | None

    fecha_creacion: datetime
    fecha_actualizacion: datetime