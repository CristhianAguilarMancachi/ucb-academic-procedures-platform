from __future__ import annotations

import os

from contextlib import (
    asynccontextmanager,
)

from decimal import Decimal

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    status,
)

from mock_pago_api.database import (
    buscar_factura,
    inicializar_base_datos,
)

from mock_pago_api.schemas import (
    FacturaValidarRequest,
    FacturaValidarResponse,
)


# ============================================================
# INICIO DEL SERVICIO
# ============================================================


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    Inicializa la base independiente del servicio externo
    cuando arranca el contenedor.
    """
    inicializar_base_datos()

    yield


app = FastAPI(
    title=(
        "API de Facturación - "
        "Simulador Institucional"
    ),

    version="1.0.0",

    description=(
        "Servicio HTTP independiente utilizado para simular "
        "la consulta al sistema externo de pagos y facturación."
    ),

    lifespan=lifespan,
)


# ============================================================
# AUTENTICACIÓN ENTRE SISTEMAS
# ============================================================


def verificar_token(
    authorization: str | None = Header(
        default=None,
    ),
) -> None:
    """
    Protege la comunicación entre M03 y el servicio externo.

    Si MOCK_PAGO_API_TOKEN está configurado, el backend debe
    enviar:

        Authorization: Bearer <token>

    El token se obtiene del entorno y nunca se escribe
    directamente en este archivo.
    """
    token_esperado = os.getenv(
        "MOCK_PAGO_API_TOKEN",
        "",
    ).strip()

    if not token_esperado:
        return

    if authorization is None:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),

            detail=(
                "Se requiere autenticación "
                "para consultar la API."
            ),
        )

    esquema, separador, token = (
        authorization.partition(
            " "
        )
    )

    if (
        not separador
        or esquema.lower() != "bearer"
        or token.strip() != token_esperado
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),

            detail=(
                "Credencial de API inválida."
            ),
        )


# ============================================================
# HEALTH CHECK
# ============================================================


@app.get(
    "/health",
    status_code=(
        status.HTTP_200_OK
    ),
)
def health() -> dict[str, str]:
    """
    Permite comprobar que el servicio externo está disponible.
    """
    return {
        "status": "ok",
    }


# ============================================================
# CONSULTA DE FACTURA
# ============================================================


@app.post(
    "/api/v1/facturas/validar",

    response_model=(
        FacturaValidarResponse
    ),

    status_code=(
        status.HTTP_200_OK
    ),

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
    Consulta una factura procesada.

    ========================================================
    DATOS QUE RECIBE
    ========================================================

    M03 envía:

        documento_identidad
        codigo
        numero_factura

    El estudiante únicamente escribe numero_factura.

    documento_identidad se obtiene desde la solicitud y
    codigo corresponde al Cod. Servicio del requisito
    económico.


    ========================================================
    CRITERIO DE BÚSQUEDA
    ========================================================

    La factura debe coincidir simultáneamente con:

        Número de factura
        CI
        Cod. Servicio

    Si alguno no coincide, la respuesta pública es la misma:

        encontrada = False

    De esta forma el servicio no revela si falló el CI,
    el código o el número ingresado.


    ========================================================
    QUÉ SIGNIFICA QUE EXISTA UNA FACTURA
    ========================================================

    En este simulador toda factura almacenada representa un
    pago que ya fue realizado y procesado fuera de M03.

    Si el estudiante todavía no realizó el pago, simplemente
    no dispone de una factura para registrar.
    """

    # --------------------------------------------------------
    # 1. BUSCAR POR NÚMERO DE FACTURA
    # --------------------------------------------------------

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
                "No se encontró una factura que "
                "coincida con los datos consultados."
            ),
        )


    # --------------------------------------------------------
    # 2. COMPROBAR CI
    # --------------------------------------------------------

    documento_real = str(
        factura[
            "documento_identidad"
        ]
        or ""
    ).strip()

    if (
        documento_real
        != datos.documento_identidad
    ):
        return FacturaValidarResponse(
            encontrada=False,

            numero_factura=(
                datos.numero_factura
            ),

            mensaje=(
                "No se encontró una factura que "
                "coincida con los datos consultados."
            ),
        )


    # --------------------------------------------------------
    # 3. COMPROBAR COD. SERVICIO
    # --------------------------------------------------------

    codigo_real = str(
        factura[
            "codigo_concepto"
        ]
    ).strip()

    if (
        codigo_real
        != datos.codigo
    ):
        return FacturaValidarResponse(
            encontrada=False,

            numero_factura=(
                datos.numero_factura
            ),

            mensaje=(
                "No se encontró una factura que "
                "coincida con los datos consultados."
            ),
        )


    # --------------------------------------------------------
    # 4. FACTURA ENCONTRADA
    # --------------------------------------------------------
    #
    # Si llegamos hasta aquí coinciden:
    #
    # - número de factura;
    # - CI;
    # - Cod. Servicio.
    #
    # También devolvemos monto y moneda para que M03 pueda
    # contrastarlos contra el requisito económico snapshot.
    # --------------------------------------------------------

    monto_real = Decimal(
        str(
            factura[
                "monto_pagado"
            ]
        )
    )

    moneda_real = str(
        factura[
            "moneda"
        ]
    ).strip().upper()


    return FacturaValidarResponse(
        encontrada=True,

        documento_identidad=(
            documento_real
        ),

        numero_factura=(
            str(
                factura[
                    "numero_factura"
                ]
            )
        ),

        codigo=(
            codigo_real
        ),

        monto=(
            monto_real
        ),

        moneda=(
            moneda_real
        ),

        # El backend actual espera este campo.
        # Toda factura de este simulador ya corresponde
        # a un pago procesado.
        estado_factura=(
            "pagada"
        ),

        # La reutilización de una factura entre solicitudes
        # es responsabilidad de M03.
        utilizada=False,

        mensaje=(
            "Factura encontrada correctamente."
        ),
    )