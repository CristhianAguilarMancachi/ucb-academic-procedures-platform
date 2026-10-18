
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.gestion_seguimiento.seguimiento import (
    HistorialResponse,
    ObservacionResponse,
    ResultadoResponse,
)

from app.schemas.gestion_seguimiento.solicitud import (
    EstadoSolicitud,
)


EstadoSolicitudAdministrativa = EstadoSolicitud

EstadoVerificacionRequisito = Literal[
    "pendiente",
    "cumple",
    "no_cumple",
]

TipoIntervencion = Literal[
    "ninguna",
    "firma",
    "conformidad",
]


# ============================================================
# BANDEJA ADMINISTRATIVA
# ============================================================

class SolicitudAdministrativaResumenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_solicitud: int
    id_solicitante: int

    nombre_solicitante: str
    documento_identidad: str | None = None

    id_tramite: int
    nombre_tramite: str

    estado: str
    tipo_intervencion: TipoIntervencion = "ninguna"

    fecha_creacion: datetime
    fecha_envio: datetime | None
    fecha_actualizacion: datetime | None = None


class ListaSolicitudesAdministrativasResponse(BaseModel):
    items: list[SolicitudAdministrativaResumenResponse]

    total: int
    pagina: int
    limite: int


# ============================================================
# DATOS DINÁMICOS
# ============================================================

class SolicitudDatoAdministrativoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_solicitud_dato: int
    id_campo: int

    clave_snapshot: str | None
    etiqueta_snapshot: str | None

    valor: Any


# ============================================================
# REQUISITOS
# ============================================================

class SolicitudRequisitoAdministrativoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_solicitud_requisito: int
    id_requisito_origen: int | None

    nombre: str
    descripcion: str | None

    obligatorio: bool
    orden: int

    requiere_presentacion_fisica: bool
    presentado: bool

    fecha_presentacion: datetime | None
    id_usuario_presentacion: int | None

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

    # Compatibilidad con registros y clientes anteriores.

    @property
    def es_economico(self) -> bool:
        return self.concepto_economico is not None


# ============================================================
# RECEPCIÓN
# ============================================================

class SolicitudRecepcionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_recepcion: int
    id_solicitud: int

    id_usuario_receptor: int
    fecha_recepcion: datetime


# ============================================================
# DETALLE ADMINISTRATIVO
# ============================================================

class SolicitudAdministrativaDetalleResponse(BaseModel):
    id_solicitud: int
    id_solicitante: int

    id_tramite: int
    nombre_tramite: str
    nombre_solicitante: str

    estado: str

    tipo_finalizacion: str | None
    tipo_intervencion: TipoIntervencion = "ninguna"

    fecha_creacion: datetime
    fecha_envio: datetime | None

    perfil_academico: dict[str, Any] | None

    datos: list[
        SolicitudDatoAdministrativoResponse
    ]

    requisitos: list[
        SolicitudRequisitoAdministrativoResponse
    ]

    recepcion: SolicitudRecepcionResponse | None

    observaciones: list[ObservacionResponse]
    historial: list[HistorialResponse]

    resultado: ResultadoResponse | None

    pagos: list[dict[str, Any]]

    # Compatibilidad temporal con Angular.



# ============================================================
# VERIFICACIÓN MANUAL EXISTENTE
# ============================================================

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

        valor = valor.strip()
        return valor or None


class RequisitoVerificacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_solicitud_requisito: int

    estado_verificacion: EstadoVerificacionRequisito

    id_usuario_verificador: int | None
    fecha_verificacion: datetime | None

    detalle_verificacion: str | None


# ============================================================
# CONFIRMACIÓN DE REQUISITOS ADMINISTRATIVOS
# ============================================================

class RequisitosAdministrativosConfirmarRequest(BaseModel):
    """
    Confirma uno o varios requisitos administrativos
    de una misma solicitud.

    No admite requisitos económicos ni documentos físicos.
    La selección se realiza desde el modal administrativo.
    """

    ids_requisitos: list[int] = Field(
        min_length=1,
        max_length=100,
    )

    detalle: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("ids_requisitos")
    @classmethod
    def validar_ids_requisitos(
        cls,
        valores: list[int],
    ) -> list[int]:
        if any(valor <= 0 for valor in valores):
            raise ValueError(
                "Los identificadores deben ser positivos."
            )

        if len(valores) != len(set(valores)):
            raise ValueError(
                "No se puede seleccionar un requisito dos veces."
            )

        return valores

    @field_validator("detalle")
    @classmethod
    def normalizar_detalle_confirmacion(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        return valor.strip() or None


class RequisitosAdministrativosConfirmarResponse(BaseModel):
    mensaje: str

    id_solicitud: int

    requisitos_confirmados: list[int] = Field(
        default_factory=list,
    )

    cantidad_confirmada: int = Field(
        ge=0,
    )

    @model_validator(mode="after")
    def validar_cantidad(
        self,
    ) -> RequisitosAdministrativosConfirmarResponse:
        if self.cantidad_confirmada != len(
            self.requisitos_confirmados
        ):
            raise ValueError(
                "La cantidad confirmada no coincide "
                "con los requisitos registrados."
            )

        return self
