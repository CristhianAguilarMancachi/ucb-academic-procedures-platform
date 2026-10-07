from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models.usuario import Usuario
from app.repositories.usuario_correo_repository import (
    crear_correo,
    marcar_correo_verificado,
    obtener_correo_activo_por_direccion,
)
from app.repositories.usuario_identidad_externa_repository import (
    crear_identidad_externa,
    obtener_identidad_externa,
    obtener_identidad_usuario_proveedor,
)
from app.repositories.usuario_repository import (
    actualizar_estado_usuario,
    actualizar_ultimo_acceso,
    crear_usuario,
    obtener_usuario_por_correo,
    obtener_usuario_por_id_completo,
)
from app.schemas.auth import LoginResponse

from app.schemas.usuario import (
    UsuarioAutenticadoResponse,
)
from app.services.auth.audit_service import (
    registrar_accion_simple,
    registrar_evento_simple,
)
from app.services.auth.google_token_service import (
    IdentidadGoogle,
    verificar_token_google,
)
from app.services.auth.role_service import (
    asignar_rol_solicitante,
)
from app.services.auth.session_service import (
    NuevaSesionResultado,
    preparar_nueva_sesion,
)


PROVEEDOR_GOOGLE = "google"


# ============================================================
# EXCEPCIONES
# ============================================================

class GoogleAuthServiceError(Exception):
    """
    Error base del flujo de autenticación con Google.
    """


class GoogleCuentaBloqueadaError(GoogleAuthServiceError):
    """
    La identidad corresponde a una cuenta bloqueada.
    """


class GoogleCuentaInactivaError(GoogleAuthServiceError):
    """
    La identidad corresponde a una cuenta inactiva.
    """


class GoogleIdentidadEnConflictoError(GoogleAuthServiceError):
    """
    La cuenta interna ya tiene vinculada otra identidad Google.
    """


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _tipo_correo(
    correo: str,
) -> str:
    """
    Clasifica el correo según el dominio institucional.
    """
    correo_normalizado = correo.strip().lower()

    if correo_normalizado.endswith(
        "@ucb.edu.bo"
    ):
        return "institucional"

    return "personal"


def _validar_estado_usuario(
    usuario: Usuario,
) -> None:
    """
    Impide que Google omita las restricciones internas
    de estado de cuenta.
    """
    if usuario.estado == "bloqueado":
        raise GoogleCuentaBloqueadaError(
            "La cuenta se encuentra bloqueada."
        )

    if usuario.estado == "inactivo":
        raise GoogleCuentaInactivaError(
            "La cuenta se encuentra inactiva."
        )

def _obtener_roles_activos_usuario(
    usuario: Usuario,
) -> list:
    """
    Obtiene únicamente los roles activos del usuario.
    """
    return [
        asignacion.rol
        for asignacion in usuario.asignaciones_rol
        if (
            asignacion.activo
            and asignacion.fecha_revocacion is None
            and asignacion.rol is not None
            and asignacion.rol.activo
        )
    ]
    
def _construir_usuario_autenticado(
    usuario: Usuario,
) -> UsuarioAutenticadoResponse:
    """
    Construye una respuesta segura del usuario autenticado.

    Nunca expone contrasena_hash. Únicamente informa si
    existe una contraseña local configurada.
    """
    return UsuarioAutenticadoResponse(
        id_usuario=usuario.id_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        telefono=usuario.telefono,
        estado=usuario.estado,
        fecha_ultimo_acceso=usuario.fecha_ultimo_acceso,
        fecha_creacion=usuario.fecha_creacion,
        fecha_actualizacion=usuario.fecha_actualizacion,
        tiene_contrasena=(
            usuario.contrasena_hash
            is not None
        ),
        correos=usuario.correos,
        roles=_obtener_roles_activos_usuario(
            usuario
        ),
    )


def _obtener_usuario_por_identidad(
    db: Session,
    identidad: IdentidadGoogle,
) -> Usuario | None:
    """
    Primero busca por el identificador estable `sub`.

    Si aún no existe vínculo, busca por correo verificado para
    permitir vincular una cuenta creada previamente mediante
    registro tradicional.
    """
    identidad_guardada = obtener_identidad_externa(
        db,
        proveedor=PROVEEDOR_GOOGLE,
        identificador_proveedor=identidad.sub,
    )

    if identidad_guardada is not None:
        return obtener_usuario_por_id_completo(
            db,
            identidad_guardada.id_usuario,
        )

    return obtener_usuario_por_correo(
        db,
        identidad.correo,
        solo_correo_activo=True,
    )


def _preparar_usuario_nuevo(
    db: Session,
    *,
    identidad: IdentidadGoogle,
) -> Usuario:
    """
    Crea una cuenta nueva autenticada exclusivamente mediante
    Google.

    El correo ya fue verificado por Google, por lo que la cuenta
    puede crearse directamente en estado activo.
    """
    ahora = utc_now()

    usuario = crear_usuario(
        db,
        nombres=identidad.nombres,
        apellidos=identidad.apellidos,
        contrasena_hash=None,
        estado="activo",
    )

    crear_correo(
        db,
        id_usuario=usuario.id_usuario,
        correo=identidad.correo,
        tipo=_tipo_correo(
            identidad.correo
        ),
        es_principal=True,
        verificado=True,
        fecha_verificacion=ahora,
    )

    asignar_rol_solicitante(
        db,
        id_usuario=usuario.id_usuario,
    )

    crear_identidad_externa(
        db,
        id_usuario=usuario.id_usuario,
        proveedor=PROVEEDOR_GOOGLE,
        identificador_proveedor=identidad.sub,
    )

    registrar_evento_simple(
        db,
        id_usuario=usuario.id_usuario,
        correo_intentado=identidad.correo,
        tipo_evento="registro",
        exitoso=True,
    )

    registrar_accion_simple(
        db,
        id_usuario_actor=usuario.id_usuario,
        accion="crear_cuenta_google",
        modulo="autenticacion",
        entidad="usuario",
        id_entidad=usuario.id_usuario,
    )

    return usuario


def _preparar_usuario_existente(
    db: Session,
    *,
    usuario: Usuario,
    identidad: IdentidadGoogle,
) -> Usuario:
    """
    Vincula Google con una cuenta previamente existente.

    Si la cuenta estaba pendiente de verificación y Google ha
    verificado el mismo correo, se considera demostrado el
    control de ese correo y se activa la cuenta.
    """
    _validar_estado_usuario(
        usuario
    )

    identidad_usuario = (
        obtener_identidad_usuario_proveedor(
            db,
            id_usuario=usuario.id_usuario,
            proveedor=PROVEEDOR_GOOGLE,
        )
    )

    if (
        identidad_usuario is not None
        and identidad_usuario.identificador_proveedor
        != identidad.sub
    ):
        raise GoogleIdentidadEnConflictoError(
            "La cuenta ya tiene otra identidad de Google vinculada."
        )

    if identidad_usuario is None:
        crear_identidad_externa(
            db,
            id_usuario=usuario.id_usuario,
            proveedor=PROVEEDOR_GOOGLE,
            identificador_proveedor=identidad.sub,
        )

        registrar_accion_simple(
            db,
            id_usuario_actor=usuario.id_usuario,
            accion="vincular_google",
            modulo="autenticacion",
            entidad="usuario",
            id_entidad=usuario.id_usuario,
        )

    correo = obtener_correo_activo_por_direccion(
        db,
        identidad.correo,
    )

    if (
        correo is not None
        and correo.id_usuario == usuario.id_usuario
        and not correo.verificado
    ):
        marcar_correo_verificado(
            db,
            correo,
            fecha_verificacion=utc_now(),
        )

    if usuario.estado == "pendiente_verificacion":
        actualizar_estado_usuario(
            db,
            usuario,
            estado="activo",
        )

    return usuario


# ============================================================
# LOGIN CON GOOGLE
# ============================================================

def iniciar_sesion_google(
    db: Session,
    *,
    credential: str,
    direccion_ip: str | None = None,
    user_agent: str | None = None,
) -> LoginResponse:
    """
    Flujo completo de autenticación mediante Google.

    1. Verifica criptográficamente el ID token.
    2. Busca la identidad por `sub`.
    3. Si todavía no está vinculada, busca por correo verificado.
    4. Crea o vincula la cuenta.
    5. Genera una sesión interna normal.
    """
    identidad = verificar_token_google(
        credential
    )

    ahora = utc_now()

    try:
        usuario = _obtener_usuario_por_identidad(
            db,
            identidad,
        )

        if usuario is None:
            usuario = _preparar_usuario_nuevo(
                db,
                identidad=identidad,
            )
        else:
            usuario = _preparar_usuario_existente(
                db,
                usuario=usuario,
                identidad=identidad,
            )

        _validar_estado_usuario(
            usuario
        )

        # Volvemos a cargar el usuario para garantizar que roles
        # y correos creados dentro de la transacción estén presentes.
        usuario = obtener_usuario_por_id_completo(
            db,
            usuario.id_usuario,
        )

        if usuario is None:
            raise GoogleAuthServiceError(
                "No fue posible recuperar la cuenta autenticada."
            )

        resultado_sesion: NuevaSesionResultado = (
            preparar_nueva_sesion(
                db,
                usuario=usuario,
                direccion_ip=direccion_ip,
                user_agent=user_agent,
            )
        )

        actualizar_ultimo_acceso(
            db,
            usuario,
            fecha_ultimo_acceso=ahora,
        )

        registrar_evento_simple(
            db,
            id_usuario=usuario.id_usuario,
            correo_intentado=identidad.correo,
            tipo_evento="inicio_sesion",
            exitoso=True,
            direccion_ip=direccion_ip,
            user_agent=user_agent,
        )

        db.commit()

        usuario = obtener_usuario_por_id_completo(
            db,
            usuario.id_usuario,
        )

        if usuario is None:
            raise GoogleAuthServiceError(
                "No fue posible recuperar la cuenta autenticada."
            )

        return LoginResponse(
            access_token=resultado_sesion.access_token,
            expires_in=resultado_sesion.expires_in,
            refresh_token=resultado_sesion.refresh_token,
            usuario=_construir_usuario_autenticado(
                usuario
            ),
        )

    except IntegrityError as exc:
        db.rollback()

        raise GoogleAuthServiceError(
            "No fue posible vincular la cuenta con Google."
        ) from exc

    except Exception:
        db.rollback()
        raise