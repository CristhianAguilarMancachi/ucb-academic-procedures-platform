from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


TipoEventoAutenticacion = Literal[
    "registro",
    "verificacion_correo",
    "inicio_sesion",
    "renovacion_sesion",
    "cierre_sesion",
    "solicitud_recuperacion",
    "cambio_contrasena",
    "cambio_correo",
    "bloqueo_cuenta",
    "desbloqueo_cuenta",
]


class EventoAutenticacionCrear(BaseModel):
    """
    Datos internos para registrar un evento de autenticación.

    Este schema no será recibido directamente desde el
    frontend; lo utilizarán los servicios del backend.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    id_usuario: int | None = Field(
        default=None,
        gt=0,
    )

    correo_intentado: EmailStr | None = None

    tipo_evento: TipoEventoAutenticacion
    exitoso: bool

    motivo_fallo: str | None = Field(
        default=None,
        max_length=100,
    )

    direccion_ip: str | None = None
    user_agent: str | None = None


class EventoAutenticacionResponse(BaseModel):
    """
    Evento de autenticación almacenado en PostgreSQL.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_evento_autenticacion: int
    id_usuario: int | None

    correo_intentado: EmailStr | None

    tipo_evento: TipoEventoAutenticacion
    exitoso: bool
    motivo_fallo: str | None

    direccion_ip: str | None
    user_agent: str | None

    fecha_evento: datetime


class ListaEventosAutenticacionResponse(BaseModel):
    """
    Respuesta paginada para consultar eventos de acceso.
    """

    items: list[EventoAutenticacionResponse]

    total: int = Field(
        ge=0,
    )

    pagina: int = Field(
        ge=1,
    )

    por_pagina: int = Field(
        ge=1,
        le=100,
    )


class AuditoriaCrear(BaseModel):
    """
    Datos internos utilizados para registrar una acción
    sensible en el sistema.

    Este schema será utilizado por audit_service.py.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    id_usuario_actor: int | None = Field(
        default=None,
        gt=0,
    )

    accion: str = Field(
        min_length=3,
        max_length=100,
    )

    modulo: str = Field(
        min_length=3,
        max_length=50,
    )

    entidad: str | None = Field(
        default=None,
        max_length=100,
    )

    id_entidad: str | None = Field(
        default=None,
        max_length=100,
    )

    exitoso: bool = True

    detalle: dict[str, Any] | None = None

    direccion_ip: str | None = None
    user_agent: str | None = None


class AuditoriaResponse(BaseModel):
    """
    Registro de auditoría visible desde administración.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id_auditoria: int
    id_usuario_actor: int | None

    accion: str
    modulo: str

    entidad: str | None
    id_entidad: str | None

    exitoso: bool
    detalle: dict[str, Any] | None

    direccion_ip: str | None
    user_agent: str | None

    fecha_evento: datetime


class ListaAuditoriaResponse(BaseModel):
    """
    Respuesta paginada para el módulo administrativo.
    """

    items: list[AuditoriaResponse]

    total: int = Field(
        ge=0,
    )

    pagina: int = Field(
        ge=1,
    )

    por_pagina: int = Field(
        ge=1,
        le=100,
    )


class FiltroAuditoriaRequest(BaseModel):
    """
    Parámetros disponibles para filtrar auditoría.

    Se podrá usar como dependencia de consulta en FastAPI.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    id_usuario_actor: int | None = Field(
        default=None,
        gt=0,
    )

    modulo: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
    )

    accion: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )

    entidad: str | None = Field(
        default=None,
        max_length=100,
    )

    exitoso: bool | None = None

    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None

    pagina: int = Field(
        default=1,
        ge=1,
    )

    por_pagina: int = Field(
        default=20,
        ge=1,
        le=100,
    )


class FiltroEventosAutenticacionRequest(BaseModel):
    """
    Filtros administrativos para eventos de autenticación.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    id_usuario: int | None = Field(
        default=None,
        gt=0,
    )

    correo: EmailStr | None = None
    tipo_evento: TipoEventoAutenticacion | None = None
    exitoso: bool | None = None

    direccion_ip: str | None = None

    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None

    pagina: int = Field(
        default=1,
        ge=1,
    )

    por_pagina: int = Field(
        default=20,
        ge=1,
        le=100,
    )