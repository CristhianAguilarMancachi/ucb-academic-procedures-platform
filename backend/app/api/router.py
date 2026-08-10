from fastapi import APIRouter

from app.api.routes.admin_users import (
    router as admin_users_router,
)
from app.api.routes.auth import (
    router as auth_router,
)
from app.api.routes.rag import (
    router as rag_router,
)
from app.api.routes.users import (
    router as users_router,
)


api_router = APIRouter()

# Autenticación
api_router.include_router(
    auth_router,
)

# Perfil y sesiones del usuario
api_router.include_router(
    users_router,
)

# Administración de usuarios y roles
api_router.include_router(
    admin_users_router,
)

# Módulo informativo RAG existente
api_router.include_router(
    rag_router,
    prefix="/rag",
    tags=["RAG"],
)