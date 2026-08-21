from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gestion_seguimiento.solicitud_pago_verificacion import (
    SolicitudPagoVerificacion,
)


def crear_verificacion_pago(
    db: Session,
    *,
    id_solicitud_requisito: int,
    id_usuario_verificador: int,
    numero_factura_consultado: str,
    codigo_concepto_consultado: str,
    estado: str,
    codigo_concepto_reportado: str | None = None,
    estado_factura_reportado: str | None = None,
    monto_reportado: Decimal | None = None,
    moneda_reportada: str | None = None,
    detalle_respuesta: dict[str, Any] | None = None,
) -> SolicitudPagoVerificacion:
    """
    Guarda un intento de validación realizado contra
    la API externa.

    No realiza commit.
    """
    verificacion = SolicitudPagoVerificacion(
        id_solicitud_requisito=(
            id_solicitud_requisito
        ),
        id_usuario_verificador=(
            id_usuario_verificador
        ),
        numero_factura_consultado=(
            numero_factura_consultado
        ),
        codigo_concepto_consultado=(
            codigo_concepto_consultado
        ),
        codigo_concepto_reportado=(
            codigo_concepto_reportado
        ),
        estado_factura_reportado=(
            estado_factura_reportado
        ),
        monto_reportado=monto_reportado,
        moneda_reportada=moneda_reportada,
        estado=estado,
        detalle_respuesta=detalle_respuesta,
    )

    db.add(verificacion)
    db.flush()
    db.refresh(verificacion)

    return verificacion


def obtener_verificacion_exitosa_por_factura(
    db: Session,
    numero_factura: str,
) -> SolicitudPagoVerificacion | None:
    """
    Determina si una factura ya acreditó exitosamente
    algún requisito dentro del sistema.
    """
    consulta = select(
        SolicitudPagoVerificacion
    ).where(
        SolicitudPagoVerificacion.numero_factura_consultado
        == numero_factura,
        SolicitudPagoVerificacion.estado
        == "verificado",
    )

    return db.scalars(
        consulta
    ).one_or_none()


def listar_verificaciones_requisito(
    db: Session,
    id_solicitud_requisito: int,
) -> Sequence[SolicitudPagoVerificacion]:
    """
    Conserva el historial de intentos de validación
    de un requisito económico.
    """
    consulta = (
        select(
            SolicitudPagoVerificacion
        )
        .where(
            SolicitudPagoVerificacion.id_solicitud_requisito
            == id_solicitud_requisito
        )
        .order_by(
            SolicitudPagoVerificacion.fecha_verificacion.asc(),
            SolicitudPagoVerificacion.id_verificacion_pago.asc(),
        )
    )

    return db.scalars(
        consulta
    ).all()