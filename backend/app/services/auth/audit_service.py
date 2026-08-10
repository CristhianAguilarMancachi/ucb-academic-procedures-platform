from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.evento_autenticacion import EventoAutenticacion
from app.repositories.auditoria_repository import (
    crear_registro_auditoria,
)
from app.repositories.evento_autenticacion_repository import (
    crear_evento_autenticacion,
)
from app.schemas.auditoria import (
    AuditoriaCrear,
    EventoAutenticacionCrear,
)


def registrar_evento_autenticacion(
    db: Session,
    datos: EventoAutenticacionCrear,
) -> EventoAutenticacion:
    """
    Registra un evento relacionado con autenticación.

    No realiza commit, porque normalmente forma parte de una
    operación mayor como registro, login, logout o recuperación.
    """
    return crear_evento_autenticacion(
        db,
        id_usuario=datos.id_usuario,
        correo_intentado=(
            str(datos.correo_intentado)
            if datos.correo_intentado
            else None
        ),
        tipo_evento=datos.tipo_evento,
        exitoso=datos.exitoso,
        motivo_fallo=datos.motivo_fallo,
        direccion_ip=datos.direccion_ip,
        user_agent=datos.user_agent,
    )


def registrar_auditoria(
    db: Session,
    datos: AuditoriaCrear,
) -> Auditoria:
    """
    Registra una acción sensible realizada en el sistema.

    No realiza commit para que el servicio que ejecuta la
    operación controle la transacción completa.
    """
    return crear_registro_auditoria(
        db,
        id_usuario_actor=datos.id_usuario_actor,
        accion=datos.accion,
        modulo=datos.modulo,
        entidad=datos.entidad,
        id_entidad=datos.id_entidad,
        exitoso=datos.exitoso,
        detalle=datos.detalle,
        direccion_ip=datos.direccion_ip,
        user_agent=datos.user_agent,
    )


def registrar_accion_simple(
    db: Session,
    *,
    accion: str,
    modulo: str,
    id_usuario_actor: int | None = None,
    entidad: str | None = None,
    id_entidad: int | str | None = None,
    exitoso: bool = True,
    detalle: dict[str, Any] | None = None,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> Auditoria:
    """
    Forma abreviada para registrar auditoría desde otros
    servicios sin construir manualmente el schema.
    """
    datos = AuditoriaCrear(
        id_usuario_actor=id_usuario_actor,
        accion=accion,
        modulo=modulo,
        entidad=entidad,
        id_entidad=(
            str(id_entidad)
            if id_entidad is not None
            else None
        ),
        exitoso=exitoso,
        detalle=detalle,
        direccion_ip=direccion_ip,
        user_agent=user_agent,
    )

    return registrar_auditoria(
        db,
        datos,
    )


def registrar_evento_simple(
    db: Session,
    *,
    tipo_evento: str,
    exitoso: bool,
    id_usuario: int | None = None,
    correo_intentado: str | None = None,
    motivo_fallo: str | None = None,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> EventoAutenticacion:
    """
    Forma abreviada para registrar eventos de autenticación.
    """
    datos = EventoAutenticacionCrear(
        id_usuario=id_usuario,
        correo_intentado=correo_intentado,
        tipo_evento=tipo_evento,
        exitoso=exitoso,
        motivo_fallo=motivo_fallo,
        direccion_ip=direccion_ip,
        user_agent=user_agent,
    )

    return registrar_evento_autenticacion(
        db,
        datos,
    )