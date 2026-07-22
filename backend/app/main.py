from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router

app = FastAPI(
    title="UCB Academic Procedures Platform API",
    version="0.1.0",
    description="Backend para gestión de trámites académicos y módulo informativo RAG."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)