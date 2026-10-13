
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from app.main import app
from mock_pago_api.database import inicializar_base_datos
from mock_pago_api.main import app as simulador_pagos


@asynccontextmanager
async def lifespan_produccion(application: FastAPI):
    token_principal = os.getenv("PAGO_API_TOKEN", "").strip()
    token_simulador = os.getenv("MOCK_PAGO_API_TOKEN", "").strip()

    if not token_principal or not token_simulador:
        raise RuntimeError(
            "La API simulada de pagos requiere tokens configurados en producción."
        )

    if token_principal != token_simulador:
        raise RuntimeError(
            "Los tokens de comunicación con el simulador no coinciden."
        )

    inicializar_base_datos()

    yield


app.router.lifespan_context = lifespan_produccion

app.mount(
    "/_internal/mock-pagos",
    simulador_pagos,
    name="simulador_pagos",
)
