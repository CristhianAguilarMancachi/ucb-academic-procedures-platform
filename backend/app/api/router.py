from fastapi import APIRouter

from app.api.routes.admin_users import (
    router as admin_users_router,
)
from app.api.routes.auth import (
    router as auth_router,
)
from app.api.routes.gestion_seguimiento.admin_solicitudes import (
    router as admin_solicitudes_router,
)
from app.api.routes.gestion_seguimiento.admin_tramites import (
    router as admin_tramites_router,
)
from app.api.routes.gestion_seguimiento.admin_unidades import (
    router as admin_unidades_router,
)
from app.api.routes.gestion_seguimiento.perfil_academico import (
    router as perfil_academico_router,
)
from app.api.routes.gestion_seguimiento.solicitudes import (
    router as solicitudes_router,
)
from app.api.routes.gestion_seguimiento.tramites import (
    router as tramites_router,
)
from app.api.routes.rag import (
    router as rag_router,
)
from app.api.routes.users import (
    router as users_router,
)


api_router = APIRouter()


# ============================================================
# AUTENTICACIÓN Y USUARIOS
# ============================================================

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


# ============================================================
# GESTIÓN Y SEGUIMIENTO DE TRÁMITES
# ============================================================

# Catálogo visible de trámites
api_router.include_router(
    tramites_router,
)

# Perfil académico del solicitante
api_router.include_router(
    perfil_academico_router,
)

# Solicitudes del solicitante
api_router.include_router(
    solicitudes_router,
)

# Bandeja y gestión administrativa de solicitudes
api_router.include_router(
    admin_solicitudes_router,
)

# Administración de unidades
api_router.include_router(
    admin_unidades_router,
)

# Administración del catálogo de trámites
api_router.include_router(
    admin_tramites_router,
)


# ============================================================
# MÓDULO INFORMATIVO RAG
# ============================================================

api_router.include_router(
    rag_router,
    prefix="/rag",
    tags=["RAG"],
)