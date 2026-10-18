
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)


TipoFinalizacion = Literal[
    "entrega",
    "resultado_registrado",
    "externo",
]

TipoIntervencion = Literal[
    "ninguna",
    "firma",
    "conformidad",
]


# ============================================================
# CONDICIONES DE REQUISITOS
# ============================================================

class CondicionDato(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )

    origen: Literal["solicitud_dato"]
    clave: str = Field(min_length=1, max_length=100)
    operador: Literal["igual"]

    valor: (
        StrictStr
        | StrictInt
        | StrictFloat
        | StrictBool
    )


class CondicionPerfil(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    origen: Literal["perfil_academico"]

    campo: Literal[
        "codigo_estudiante",
        "sede",
        "carrera_programa",
        "nivel_academico",
        "documento_identidad",
    ]

    operador: Literal["igual"]

    valor: str = Field(
        min_length=1,
        max_length=200,
    )


CondicionRequisito = Annotated[
    CondicionDato | CondicionPerfil,
    Field(discriminator="origen"),
]


# ============================================================
# COMPATIBILIDAD CON ETAPAS ANTERIORES
# ============================================================





# ============================================================
# HISTORIAL
# ============================================================

class HistorialPublicoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_historial: int
    evento: str
    detalle: str
    fecha_evento: datetime


class HistorialResponse(HistorialPublicoResponse):
    id_solicitud_requisito: int | None = None
    id_usuario_actor: int | None
    visible_solicitante: bool


# ============================================================
# OBSERVACIONES
# ============================================================

class ObservacionCrearRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    id_solicitud_requisito: int | None = Field(
        default=None,
        gt=0,
    )

    detalle: str = Field(
        min_length=1,
        max_length=3000,
    )

    correccion_requerida: str = Field(
        min_length=1,
        max_length=3000,
    )

    canal_subsanacion: str | None = Field(
        default=None,
        max_length=1000,
    )


class ObservacionPublicaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_observacion: int
    id_solicitud_requisito: int | None

    detalle: str
    correccion_requerida: str
    canal_subsanacion: str | None

    estado: Literal[
        "pendiente",
        "resuelta",
    ]

    fecha_observacion: datetime
    fecha_resolucion: datetime | None


class ObservacionResponse(
    ObservacionPublicaResponse
):
    # Campo heredado del diseño anterior.
    # Las observaciones actuales ya no dependen de
    # una etapa específica de la solicitud.

    id_usuario_observador: int
    id_usuario_resolucion: int | None


# ============================================================
# PETICIONES GENERALES
# ============================================================

class MotivoRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    motivo: str = Field(
        min_length=1,
        max_length=2000,
    )


class FacturaRegistrarRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    numero_factura: str = Field(
        min_length=1,
        max_length=150,
    )


# ============================================================
# RESULTADOS
# ============================================================

class ResultadoRegistrarRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    detalle: str | None = Field(
        default=None,
        max_length=3000,
    )

    tipo_finalizacion: TipoFinalizacion | None = None


class ResultadoPublicoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tipo_finalizacion: TipoFinalizacion
    detalle: str | None
    fecha_registro: datetime


class ResultadoResponse(
    ResultadoPublicoResponse
):
    id_resultado: int
    id_usuario_registro: int


# ============================================================
# ENTREGA
# ============================================================



# ============================================================
# SEGUIMIENTO PÚBLICO
# ============================================================

class SeguimientoResponse(BaseModel):
    id_solicitud: int
    identificador: str
    nombre_tramite: str

    estado: str

    tipo_intervencion: TipoIntervencion = "ninguna"

    observaciones: list[
        ObservacionPublicaResponse
    ]

    observaciones_pendientes: int

    historial: list[
        HistorialPublicoResponse
    ]

    resultado: ResultadoPublicoResponse | None

    # Compatibilidad con el frontend anterior.


    avance_porcentaje: int = 0
    