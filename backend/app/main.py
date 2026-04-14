from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(
    title="UCB Academic Procedures Platform API",
    version="0.1.0",
    description="Backend para gestión de trámites académicos y módulo informativo RAG."
)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "message": "API running",
        "service": "ucb-academic-procedures-platform"
    }