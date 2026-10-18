
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.schemas.gestion_seguimiento.notificacion import (
    NotificacionResponse,
)


TipoIntervencion = Literal["conformidad", "firma"]

EstadoIntervencion = Literal[
    "convocada",
    "conforme",
    "no_conforme",
    "firmada",
    "anulada",
]


class RevisionPresencialRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    resultado: Literal[
        "conforme",
        "no_conforme",
        "firmada",
    ]

    fecha_revision: date

    motivo_desacuerdo: str | None = Field(
        default=None,
        max_length=2000,
    )

    @model_validator(mode="after")
    def validar_revision(self):
        hoy = datetime.now(
            ZoneInfo("America/La_Paz")
        ).date()

        if self.fecha_revision > hoy:
            raise ValueError(
                "La fecha de revisión no puede ser futura."
            )

        if self.resultado == "no_conforme":
            if (
                not self.motivo_desacuerdo
                or not self.motivo_desacuerdo.strip()
            ):
                raise ValueError(
                    "Indica el motivo del desacuerdo."
                )

        elif self.motivo_desacuerdo is not None:
            raise ValueError(
                "El motivo solo corresponde "
                "a una revisión no conforme."
            )

        return self


class IntervencionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_intervencion: int
    id_solicitud: int

    tipo: TipoIntervencion
    estado: EstadoIntervencion

    id_usuario_convocatoria: int
    fecha_convocatoria: datetime

    fecha_revision: date | None
    id_usuario_registro: int | None
    fecha_registro: datetime | None

    motivo_desacuerdo: str | None


class ConvocatoriaResponse(BaseModel):
    intervencion: IntervencionResponse
    notificacion: NotificacionResponse


class ResolucionEmitidaResponse(BaseModel):
    id_historial: int
    id_solicitud: int
    id_usuario_actor: int
    fecha_emision: datetime
    detalle: str
