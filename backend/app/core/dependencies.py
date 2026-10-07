from __future__ import annotations

from collections.abc import Callable
from typing import Annotated


from fastapi import (
    Depends,
    HTTPException,
    status,
)

from fastapi.security import (
    OAuth2PasswordBearer,
)
from sqlalchemy.orm import Session



from app.core.security import (
    TokenExpiradoError,
    TokenInvalidoError,
    decodificar_access_token,
    utc_now,
)

from app.db.session import get_db

from app.models.usuario import Usuario
from app.repositories.usuario_repository import (
    obtener_usuario_por_id_completo,
    tiene_correo_principal_verificado,
)
from app.repositories.sesion_usuario_repository import (
    obtener_sesion_por_identificador_y_usuario,
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    auto_error=True,
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]

AccessToken = Annotated[
    str,
    Depends(oauth2_scheme),
]


def credenciales_invalidas_exception() -> HTTPException:
    """
    Respuesta uniforme para credenciales inválidas.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "No fue posible validar las credenciales."
        ),
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def obtener_usuario_actual(
    db: DatabaseSession,
    token: AccessToken,
) -> Usuario:
    """
    Obtiene el usuario asociado al access token y valida:

    - firma y expiración del JWT;
    - existencia de la cuenta;
    - existencia de la sesión;
    - pertenencia de la sesión al usuario;
    - vigencia y no revocación de la sesión.
    """
    try:
        payload = decodificar_access_token(token)
        id_usuario = int(payload.sub)

    except (
        TokenExpiradoError,
        TokenInvalidoError,
        ValueError,
        TypeError,
    ):
        raise credenciales_invalidas_exception()

    usuario = obtener_usuario_por_id_completo(
        db,
        id_usuario,
    )
    

    if usuario is None:
        raise credenciales_invalidas_exception()

    sesion = obtener_sesion_por_identificador_y_usuario(
        db,
        identificador_sesion=payload.session_id,
        id_usuario=usuario.id_usuario,
    )

    if sesion is None:
        raise credenciales_invalidas_exception()

    if (
        sesion.fecha_revocacion is not None
        or sesion.fecha_expiracion <= utc_now()
    ):
        raise credenciales_invalidas_exception()

    return usuario


UsuarioActual = Annotated[
    Usuario,
    Depends(obtener_usuario_actual),
]


def obtener_usuario_activo(
    usuario: UsuarioActual,
) -> Usuario:
    """
    Permite continuar únicamente a cuentas activas.
    """
    if usuario.estado == "bloqueado":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "La cuenta se encuentra bloqueada."
            ),
        )

    if usuario.estado == "inactivo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "La cuenta se encuentra inactiva."
            ),
        )

    if usuario.estado == "pendiente_verificacion":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Debes verificar tu correo antes "
                "de utilizar esta función."
            ),
        )

    if usuario.estado != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "La cuenta no está habilitada."
            ),
        )

    if not tiene_correo_principal_verificado(usuario):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes verificar tu correo principal antes de utilizar esta función.",
        )

    return usuario


UsuarioActivo = Annotated[
    Usuario,
    Depends(obtener_usuario_activo),
]


def exigir_roles(
    *roles_permitidos: str,
) -> Callable[[UsuarioActivo], Usuario]:
    """
    Crea una dependencia que exige al menos uno de los roles
    indicados.

    Ejemplo:
        Depends(exigir_roles("administrador"))
    """
    roles_normalizados = {
        rol.strip().lower()
        for rol in roles_permitidos
        if rol.strip()
    }

    if not roles_normalizados:
        raise ValueError(
            "Debe indicarse al menos un rol permitido."
        )

    def dependency(
        usuario: UsuarioActivo,
    ) -> Usuario:
        roles_usuario = {
            asignacion.rol.nombre.strip().lower()
            for asignacion
            in usuario.asignaciones_rol
            if (
                asignacion.activo
                and asignacion.fecha_revocacion is None
                and asignacion.rol.activo
            )
        }

        if roles_usuario.isdisjoint(
            roles_normalizados
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "No tienes permisos para realizar "
                    "esta operación."
                ),
            )

        return usuario

    return dependency


def exigir_administrador(
    usuario: Annotated[
        Usuario,
        Depends(
            exigir_roles(
                "administrador",
            )
        ),
    ],
) -> Usuario:
    """
    Permite únicamente el rol administrador.
    """
    return usuario


AdministradorActual = Annotated[
    Usuario,
    Depends(exigir_administrador),
]


def exigir_personal_administrativo(
    usuario: Annotated[
        Usuario,
        Depends(
            exigir_roles(
                "personal_administrativo",
                "administrador",
            )
        ),
    ],
) -> Usuario:
    """
    Permite personal administrativo o administradores.
    """
    return usuario


PersonalAdministrativoActual = Annotated[
    Usuario,
    Depends(exigir_personal_administrativo),
]


def exigir_solicitante(
    usuario: Annotated[
        Usuario,
        Depends(
            exigir_roles(
                "solicitante",
                "personal_administrativo",
                "administrador",
            )
        ),
    ],
) -> Usuario:
    """
    Permite cualquier cuenta con un rol funcional activo.
    """
    return usuario


SolicitanteActual = Annotated[
    Usuario,
    Depends(exigir_solicitante),
]