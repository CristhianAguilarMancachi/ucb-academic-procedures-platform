# ============================================================
# MODELOS DE AUTENTICACIÓN Y SEGURIDAD
# ============================================================

from app.models.usuario import Usuario
from app.models.usuario_correo import UsuarioCorreo
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol
from app.models.sesion_usuario import SesionUsuario
from app.models.token_verificacion_correo import TokenVerificacionCorreo
from app.models.token_recuperacion_contrasena import (
    TokenRecuperacionContrasena,
)
from app.models.evento_autenticacion import EventoAutenticacion
from app.models.auditoria import Auditoria


# ============================================================
# MODELOS DEL MÓDULO INFORMATIVO RAG
# ============================================================

from app.models.documento_institucional import DocumentoInstitucional
from app.models.version_documento import VersionDocumento
from app.models.chunk_documento import ChunkDocumento


# ============================================================
# MODELOS DEL HISTORIAL DE CONVERSACIÓN
# ============================================================

from app.models.chat.chat_session import ChatSession
from app.models.chat.chat_message import ChatMessage


__all__ = [
    # Autenticación y seguridad
    "Usuario",
    "UsuarioCorreo",
    "Rol",
    "UsuarioRol",
    "SesionUsuario",
    "TokenVerificacionCorreo",
    "TokenRecuperacionContrasena",
    "EventoAutenticacion",
    "Auditoria",

    # RAG
    "DocumentoInstitucional",
    "VersionDocumento",
    "ChunkDocumento",

    # Historial de conversación
    "ChatSession",
    "ChatMessage",
]