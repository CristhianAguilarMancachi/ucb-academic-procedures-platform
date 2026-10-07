from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import CORS_ORIGINS
from app.services.gestion_seguimiento.seguimiento_service import (
    SeguimientoError,
)


# ============================================================
# APLICACIÓN FASTAPI
# ============================================================
#
# El RAG ya no necesita cargar un modelo de embeddings local
# durante el arranque. Jina AI se consume mediante API cuando
# una operación necesita generar embeddings.
# ============================================================

app = FastAPI(
    title="UCB Academic Procedures Platform API",
    version="0.1.0",
    description=(
        "Backend para gestión de trámites académicos "
        "y módulo informativo RAG."
    ),
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RUTAS DE LA API
# ============================================================

app.include_router(
    api_router,
    prefix="/api",
)


# ============================================================
# HEALTH CHECKS
# ============================================================

@app.get(
    "/health",
    tags=["Health"],
)
def health():
    return {
        "status": "ok",
    }


@app.get(
    "/ready",
    tags=["Health"],
)
def ready():
    return {
        "status": "ready",
        "rag_ready": True,
    }


# ============================================================
# MANEJO GLOBAL DE ERRORES DE SEGUIMIENTO
# ============================================================

@app.exception_handler(
    SeguimientoError
)
async def error_seguimiento(
    request,
    exc: SeguimientoError,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc),
        },
    )