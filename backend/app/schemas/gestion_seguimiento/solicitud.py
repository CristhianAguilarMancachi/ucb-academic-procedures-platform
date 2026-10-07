from __future__ import annotations

import re

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


EstadoSolicitud = Literal[
    "borrador",
    "pendiente_recepcion",
    "en_revision",
    "en_proceso",
    "lista_para_entrega",
    "finalizada",
    "cancelada",
    "rechazada",
]


# =========================================================
# DATOS DINÁMICOS DE LA SOLICITUD
# =========================================================


class SolicitudDatoGuardarRequest(BaseModel):
    id_campo: int = Field(
        gt=0
    )

    valor: Any

    @field_validator("valor")
    @classmethod
    def validar_valor_no_nulo(
        cls,
        valor: Any,
    ) -> Any:
        if valor is None:
            raise ValueError(
                "El valor del campo no puede ser nulo."
            )

        return valor


class SolicitudDatoResponse(BaseModel):
    clave_snapshot: str | None
    etiqueta_snapshot: str | None

    model_config = ConfigDict(
        from_attributes=True
    )

    id_solicitud_dato: int
    id_solicitud: int
    id_campo: int

    valor: Any

    fecha_creacion: datetime
    fecha_actualizacion: datetime


# =========================================================
# FACTURA
# =========================================================


class SolicitudFacturaGuardarRequest(BaseModel):
    id_requisito: int = Field(
        gt=0,
    )

    numero_factura: str = Field(
        min_length=1,
        max_length=150,
    )

    @field_validator(
        "numero_factura"
    )
    @classmethod
    def normalizar_numero_factura(
        cls,
        valor: str,
    ) -> str:
        valor_normalizado = (
            valor.strip()
        )

        if not valor_normalizado:
            raise ValueError(
                "El número de factura "
                "no puede estar vacío."
            )

        return valor_normalizado


# =========================================================
# ENVÍO
# =========================================================


class SolicitudEnviarRequest(BaseModel):
    """
    El envío formal ya no recibe pago ni documentación.

    El body vacío se conserva para compatibilidad con
    el cliente HTTP actual.
    """

    model_config = ConfigDict(
        extra="ignore",
    )


# =========================================================
# REQUISITOS COPIADOS
# =========================================================


class SolicitudRequisitoResponse(BaseModel):
    id_solicitud_etapa: int | None

    requiere_presentacion_fisica: bool

    presentado: bool
    fecha_presentacion: datetime | None

    estado_verificacion: str
    detalle_verificacion: str | None

    puede_registrar_factura: bool = False
    puede_declarar_entrega: bool = False
    entrega_declarada: bool = False

    model_config = ConfigDict(
        from_attributes=True
    )

    id_solicitud_requisito: int
    id_solicitud: int

    id_requisito_origen: int | None

    nombre: str
    descripcion: str | None

    obligatorio: bool
    orden: int

    id_requisito_economico_origen: int | None

    concepto_economico: str | None
    monto_economico: Decimal | None
    moneda: str | None
    gestion: int | None

    codigo_concepto_externo: str | None

    numero_factura: str | None

    fecha_creacion: datetime
    fecha_actualizacion: datetime

    @property
    def es_economico(
        self,
    ) -> bool:
        return (
            self.concepto_economico
            is not None
        )


# =========================================================
# TRÁMITE
# =========================================================


class TramiteSolicitudResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id_tramite: int

    nombre: str
    descripcion: str | None


# =========================================================
# CREACIÓN
# =========================================================


class SolicitudCrearRequest(BaseModel):
    id_tramite: int = Field(
        gt=0
    )


# =========================================================
# ACTUALIZACIÓN DE BORRADOR
# =========================================================


class SolicitudActualizarRequest(BaseModel):
    """
    Permite actualizar, mientras siga en borrador:

    - datos dinámicos del trámite;
    - nombre de contacto;
    - teléfono de contacto;
    - correo de contacto.

    Los datos de contacto pertenecen a esta solicitud y
    no modifican la cuenta del usuario.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    datos: (
        list[
            SolicitudDatoGuardarRequest
        ]
        | None
    ) = None

    nombre_contacto: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    telefono_contacto: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
    )

    correo_contacto: EmailStr | None = (
        None
    )

    @field_validator(
        "nombre_contacto"
    )
    @classmethod
    def normalizar_nombre_contacto(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        valor = " ".join(
            valor.split()
        )

        if not any(
            caracter.isalpha()
            for caracter in valor
        ):
            raise ValueError(
                "El nombre de contacto debe "
                "contener al menos una letra."
            )

        return valor

    @field_validator(
        "telefono_contacto"
    )
    @classmethod
    def validar_telefono_contacto(
        cls,
        valor: str | None,
    ) -> str | None:
        if valor is None:
            return None

        valor = valor.strip()

        if not re.fullmatch(
            r"[0-9+\-().\s]+",
            valor,
        ):
            raise ValueError(
                "El teléfono contiene "
                "caracteres no permitidos."
            )

        cantidad_digitos = len(
            re.sub(
                r"\D",
                "",
                valor,
            )
        )

        if (
            cantidad_digitos < 7
            or cantidad_digitos > 15
        ):
            raise ValueError(
                "El teléfono debe contener "
                "entre 7 y 15 dígitos."
            )

        return valor


# =========================================================
# RESPUESTAS
# =========================================================


class SolicitudResumenResponse(BaseModel):
    nombre_tramite_snapshot: str | None

    model_config = ConfigDict(
        from_attributes=True
    )

    id_solicitud: int

    id_tramite: int
    estado: EstadoSolicitud

    fecha_creacion: datetime
    fecha_envio: datetime | None
    fecha_actualizacion: datetime

    tramite: TramiteSolicitudResponse


class SolicitudResponse(BaseModel):
    documento_identidad_pago: str | None = None

    nombre_tramite_snapshot: str | None
    tipo_finalizacion: str | None

    nombre_contacto: str | None = None
    telefono_contacto: str | None = None
    correo_contacto: str | None = None

    model_config = ConfigDict(
        from_attributes=True
    )

    id_solicitud: int
    id_solicitante: int

    id_tramite: int
    estado: EstadoSolicitud

    fecha_creacion: datetime
    fecha_envio: datetime | None
    fecha_actualizacion: datetime

    tramite: TramiteSolicitudResponse

    datos: list[
        SolicitudDatoResponse
    ] = Field(
        default_factory=list
    )

    requisitos: list[
        SolicitudRequisitoResponse
    ] = Field(
        default_factory=list
    )


class ListaSolicitudesResponse(BaseModel):
    items: list[
        SolicitudResumenResponse
    ]

    total: int = Field(
        ge=0,
    )

    pagina: int = Field(
        ge=1,
    )

    por_pagina: int = Field(
        ge=1,
    )