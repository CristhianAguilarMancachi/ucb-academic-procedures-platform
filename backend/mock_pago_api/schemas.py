from __future__ import annotations

from decimal import Decimal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class FacturaValidarRequest(BaseModel):
    """
    Datos enviados por M03 al sistema externo de facturación.

    El estudiante únicamente escribe numero_factura.

    documento_identidad:
        Se obtiene desde la información de la solicitud.

    codigo:
        Corresponde al Cod. Servicio configurado para el
        requisito económico del trámite.

    numero_factura:
        Corresponde al número que el estudiante recibe en
        su factura después de realizar el pago fuera de M03.
    """

    documento_identidad: str = Field(
        min_length=3,
        max_length=50,
    )

    codigo: str = Field(
        min_length=1,
        max_length=100,
    )

    numero_factura: str = Field(
        min_length=1,
        max_length=150,
    )

    @field_validator(
        "documento_identidad",
        "codigo",
        "numero_factura",
    )
    @classmethod
    def normalizar_texto(
        cls,
        valor: str,
    ) -> str:
        """
        Elimina espacios accidentales antes de consultar.
        """
        valor_limpio = valor.strip()

        if not valor_limpio:
            raise ValueError(
                "El valor no puede estar vacío."
            )

        return valor_limpio


class FacturaValidarResponse(BaseModel):
    """
    Respuesta normalizada del sistema externo.

    encontrada=True:
        Existe una factura procesada que coincide con el
        número, CI y Cod. Servicio consultados.

    encontrada=False:
        No existe una factura que coincida con esa consulta.

    monto y moneda se devuelven para que M03 pueda
    contrastarlos contra el requisito económico de la
    solicitud.

    estado_factura y utilizada se conservan por compatibilidad
    con el contrato actual del backend principal.

    En este mock toda factura existente representa un pago ya
    procesado, por lo que:

        estado_factura = "pagada"
        utilizada = False

    La reutilización de una factura entre solicitudes la
    controla M03, no este servicio externo.
    """

    documento_identidad: str | None = None

    encontrada: bool

    numero_factura: str

    codigo: str | None = None

    monto: Decimal | None = None

    moneda: str | None = None

    estado_factura: str | None = None

    utilizada: bool | None = None

    mensaje: str | None = None