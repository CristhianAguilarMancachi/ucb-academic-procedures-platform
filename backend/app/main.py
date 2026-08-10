import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS

from app.api.router import api_router
from app.services.rag.embeddings import get_embedding_model


rag_ready = False


def prepare_rag() -> None:
    global rag_ready

    try:
        print("[STARTUP] Preparando modelo de embeddings...")
        get_embedding_model()
        rag_ready = True
        print("[STARTUP] Módulo RAG preparado.")
    except Exception as exc:
        rag_ready = False
        print(f"[STARTUP] No se pudo preparar el RAG: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(
        asyncio.to_thread(prepare_rag)
    )

    yield


app = FastAPI(
    title="UCB Academic Procedures Platform API",
    version="0.1.0",
    description=(
        "Backend para gestión de trámites académicos "
        "y módulo informativo RAG."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix="/api",
)


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok"
    }


@app.get("/ready", tags=["Health"])
def ready():
    return {
        "status": "ready" if rag_ready else "loading",
        "rag_ready": rag_ready,
    }