
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class NotificacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_notificacion: int
    id_solicitud: int
    id_intervencion: int | None

    tipo: Literal["convocatoria", "resultado"]
    estado: Literal["pendiente", "enviado", "fallido"]

    destinatario: str
    asunto: str
    contenido_texto: str

    intentos: int
    fecha_creacion: datetime
    fecha_ultimo_intento: datetime | None
    fecha_envio: datetime | None

    ultimo_error: str | None
    referencia_externa: str | None
