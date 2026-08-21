from __future__ import annotations

import os
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    status,
)

from mock_pago_api.database import (
    buscar_concepto,
    buscar_factura,
    inicializar_base_datos,
)
from mock_pago_api.schemas import (
    FacturaValidarRequest,
    FacturaValidarResponse,
)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    inicializar_base_datos()

    yield


app = FastAPI(
    title="Mock API de Pagos",
    version="1.0.0",
    description=(
        "API independiente utilizada exclusivamente para "
        "simular la integración con un sistema externo de "
        "pagos y facturación."
    ),
    lifespan=lifespan,
)


def verificar_token(
    authorization: str | None = Header(
        default=None,
    ),
) -> None:
    """
    La autenticación se activa únicamente cuando existe
    MOCK_PAGO_API_TOKEN en el entorno.

    De esa forma podemos utilizar un Bearer Token durante
    desarrollo sin incrustarlo en el código.
    """
    token_esperado = os.getenv(
        "MOCK_PAGO_API_TOKEN",
        "",
    ).strip()

    if not token_esperado:
        return

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Se requiere autenticación para "
                "consultar la API."
            ),
        )

    esquema, separador, token = (
        authorization.partition(" ")
    )

    if (
        not separador
        or esquema.lower() != "bearer"
        or token.strip() != token_esperado
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Credencial de API inválida."
            ),
        )


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.post(
    "/api/v1/facturas/validar",
    response_model=FacturaValidarResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(
            verificar_token
        )
    ],
)
def validar_factura(
    datos: FacturaValidarRequest,
) -> FacturaValidarResponse:
    """
    Consulta una factura utilizando:

        codigo
        numero_factura

    La API devuelve los hechos almacenados en su propio
    sistema.

    La decisión definitiva sobre si el requisito de una
    solicitud cumple la realiza el backend principal.
    """
    factura = buscar_factura(
        datos.numero_factura
    )

    if factura is None:
        return FacturaValidarResponse(
            encontrada=False,
            numero_factura=(
                datos.numero_factura
            ),
            mensaje=(
                "La factura indicada no existe."
            ),
        )

    codigo_real = str(
        factura["codigo_concepto"]
    )

    monto_real = Decimal(
        str(
            factura["monto_pagado"]
        )
    )

    moneda_real = str(
        factura["moneda"]
    ).upper()

    estado_real = str(
        factura["estado"]
    ).lower()

    utilizada = bool(
        factura["utilizada"]
    )

    concepto_consultado = buscar_concepto(
        datos.codigo
    )

    if concepto_consultado is None:
        mensaje = (
            "El código consultado no existe en "
            "el catálogo de pagos."
        )

    elif codigo_real != datos.codigo:
        mensaje = (
            "La factura existe, pero no corresponde "
            "al código consultado."
        )

    elif utilizada:
        mensaje = (
            "La factura ya se encuentra utilizada."
        )

    elif estado_real != "pagada":
        mensaje = (
            "La factura existe, pero no se encuentra "
            "en estado pagada."
        )

    else:
        monto_catalogo = Decimal(
            str(
                factura["monto_concepto"]
            )
        )

        moneda_catalogo = str(
            factura["moneda_concepto"]
        ).upper()

        if (
            monto_real != monto_catalogo
            or moneda_real != moneda_catalogo
        ):
            mensaje = (
                "La factura presenta valores económicos "
                "diferentes a los registrados para "
                "el concepto."
            )
        else:
            mensaje = (
                "Factura encontrada correctamente."
            )

    return FacturaValidarResponse(
        encontrada=True,
        numero_factura=(
            str(
                factura["numero_factura"]
            )
        ),
        codigo=codigo_real,
        monto=monto_real,
        moneda=moneda_real,
        estado_factura=estado_real,
        utilizada=utilizada,
        mensaje=mensaje,
    )