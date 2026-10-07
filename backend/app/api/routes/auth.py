from __future__ import annotations


from fastapi import (

    APIRouter,

    Body,

    Cookie,

    Depends,

    HTTPException,

    Request,

    Response,

    status,

)

from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session


from app.core.config import (

    COOKIE_DOMAIN,

    COOKIE_HTTPONLY,

    COOKIE_PATH,

    COOKIE_SAMESITE,

    COOKIE_SECURE,

    REFRESH_TOKEN_COOKIE_NAME,

    REFRESH_TOKEN_EXPIRE_DAYS,

    GOOGLE_CLIENT_ID,

)

from app.core.dependencies import (

    DatabaseSession,

    UsuarioActivo,

)

from app.models.usuario import Usuario

from app.schemas.auth import (

    CambioContrasenaRequest,

    LoginRequest,

    LoginResponse,

    MensajeResponse,

    RefreshTokenRequest,

    RegistroRequest,

    RegistroResponse,

    RestablecerContrasenaRequest,

    SolicitudRecuperacionRequest,

    TokenResponse,

    GoogleLoginRequest,

)

from app.schemas.correo import (

    CorreoReenviarVerificacionRequest,

    CorreoVerificarRequest,

)

from app.services.auth.auth_service import (

    AuthServiceError,

    ContrasenaActualInvalidaError,

    CorreoYaRegistradoError,

    CredencialesInvalidasError,

    CuentaBloqueadaError,

    CuentaInactivaError,

    CuentaPendienteVerificacionError,

    DemasiadosIntentosLoginError,

    cambiar_contrasena,

    iniciar_sesion,

    registrar_usuario,

)

from app.services.auth.email_verification_service import (

    CorreoNoEncontradoError,

    CorreoYaVerificadoError,

    EmailVerificationServiceError,

    EnvioVerificacionCorreoError,

    TokenVerificacionInvalidoError,

    reenviar_verificacion_correo,

    verificar_correo,

)

from app.services.auth.password_recovery_service import (

    EnvioRecuperacionCorreoError,

    PasswordRecoveryServiceError,

    TokenRecuperacionInvalidoError,

    restablecer_contrasena,

    solicitar_recuperacion_contrasena,

)

from app.services.auth.session_service import (

    RefreshTokenInvalidoError,

    SesionYaRevocadaError,

    SessionServiceError,

    cerrar_sesion_por_refresh_token,

    renovar_sesion,

)

from app.services.auth.google_auth_service import (

    GoogleAuthServiceError,

    GoogleCuentaBloqueadaError,

    GoogleCuentaInactivaError,

    GoogleIdentidadEnConflictoError,

    iniciar_sesion_google,

)


from app.services.auth.google_token_service import (

    GoogleCorreoNoVerificadoError,

    GoogleNoConfiguradoError,

    GoogleTokenInvalidoError,

)


router = APIRouter(

    prefix="/auth",

    tags=["Autenticación"],

)


# ============================================================

# FUNCIONES AUXILIARES

# ============================================================


def obtener_direccion_ip(

    request: Request,

) -> str | None:

    """

    Obtiene la dirección IP de la solicitud.


    Considera encabezados utilizados por proxies como Nginx

    y Cloudflare.

    """

    forwarded_for = request.headers.get(

        "x-forwarded-for"

    )


    if forwarded_for:

        return forwarded_for.split(",")[0].strip()


    real_ip = request.headers.get(

        "x-real-ip"

    )


    if real_ip:

        return real_ip.strip()


    if request.client is not None:

        return request.client.host


    return None


def obtener_user_agent(

    request: Request,

) -> str | None:

    """

    Obtiene información básica del navegador o cliente.

    """

    return request.headers.get(

        "user-agent"

    )


def configurar_cookie_refresh(

    response: Response,

    refresh_token: str,

) -> None:

    """

    Guarda el refresh token en una cookie HttpOnly.


    El frontend no podrá leerla mediante JavaScript, pero el

    navegador la enviará automáticamente al backend.

    """

    response.set_cookie(

        key=REFRESH_TOKEN_COOKIE_NAME,

        value=refresh_token,

        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,

        httponly=COOKIE_HTTPONLY,

        secure=COOKIE_SECURE,

        samesite=COOKIE_SAMESITE,

        path=COOKIE_PATH,

        domain=COOKIE_DOMAIN,

    )


def eliminar_cookie_refresh(

    response: Response,

) -> None:

    """

    Elimina la cookie que contiene el refresh token.

    """

    response.delete_cookie(

        key=REFRESH_TOKEN_COOKIE_NAME,

        path=COOKIE_PATH,

        domain=COOKIE_DOMAIN,

        secure=COOKIE_SECURE,

        httponly=COOKIE_HTTPONLY,

        samesite=COOKIE_SAMESITE,

    )


def resolver_refresh_token(

    token_cookie: str | None,

    datos: RefreshTokenRequest | None,

) -> str:

    if token_cookie:

        return token_cookie


    if datos is not None and datos.refresh_token is not None:

        return datos.refresh_token.get_secret_value()


    raise RefreshTokenInvalidoError(

        "No se proporcionó un refresh token."

    )


def autenticar_y_configurar_respuesta(

    *,

    db: Session,

    correo: str,

    contrasena: str,

    request: Request,

    response: Response,

) -> LoginResponse:

    """

    Ejecuta el inicio de sesión y configura la cookie segura.

    """

    resultado = iniciar_sesion(

        db,

        correo=correo,

        contrasena=contrasena,

        direccion_ip=obtener_direccion_ip(request),

        user_agent=obtener_user_agent(request),

    )


    if resultado.refresh_token is None:

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=(

                "No fue posible generar la sesión "

                "de autenticación."

            ),

        )


    configurar_cookie_refresh(

        response,

        resultado.refresh_token,

    )


    # El refresh token queda únicamente en la cookie HttpOnly.

    return resultado.model_copy(

        update={

            "refresh_token": None,

        }

    )


# ============================================================

# REGISTRO

# ============================================================


@router.post(

    "/register",

    response_model=RegistroResponse,

    status_code=status.HTTP_201_CREATED,

)

def registrar_cuenta(

    datos: RegistroRequest,

    request: Request,

    db: DatabaseSession,

) -> RegistroResponse:

    """

    Crea una cuenta pendiente de verificación, asigna el rol

    solicitante y genera el correo de confirmación.

    """

    try:

        return registrar_usuario(

            db,

            datos=datos,

            direccion_ip=obtener_direccion_ip(request),

            user_agent=obtener_user_agent(request),

        )


    except CorreoYaRegistradoError as exc:

        raise HTTPException(

            status_code=status.HTTP_409_CONFLICT,

            detail=str(exc),

        ) from exc


    except AuthServiceError as exc:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(exc),

        ) from exc


# ============================================================

# LOGIN JSON PARA ANGULAR

# ============================================================


@router.post(

    "/login",

    response_model=LoginResponse,

    status_code=status.HTTP_200_OK,

)

def login(

    datos: LoginRequest,

    request: Request,

    response: Response,

    db: DatabaseSession,

) -> LoginResponse:

    """

    Inicia sesión mediante un cuerpo JSON.


    Este endpoint será utilizado normalmente por Angular.

    """

    try:

        return autenticar_y_configurar_respuesta(

            db=db,

            correo=str(datos.correo),

            contrasena=(

                datos.contrasena.get_secret_value()

            ),

            request=request,

            response=response,

        )


    except CredencialesInvalidasError as exc:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail=str(exc),

            headers={

                "WWW-Authenticate": "Bearer",

            },

        ) from exc


    except DemasiadosIntentosLoginError as exc:

        raise HTTPException(

            status_code=status.HTTP_429_TOO_MANY_REQUESTS,

            detail=str(exc),

        ) from exc


    except CuentaPendienteVerificacionError as exc:

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail=str(exc),

        ) from exc


    except (

        CuentaBloqueadaError,

        CuentaInactivaError,

    ) as exc:

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail=str(exc),

        ) from exc


# ============================================================

# LOGIN PARA SWAGGER

# ============================================================


@router.post(

    "/token",

    response_model=TokenResponse,

    status_code=status.HTTP_200_OK,

)

def obtener_token_swagger(

    request: Request,

    response: Response,

    db: DatabaseSession,

    formulario: OAuth2PasswordRequestForm = Depends(),

) -> TokenResponse:

    """

    Endpoint OAuth2 utilizado por el botón Authorize de Swagger.


    En el campo username se debe introducir el correo.

    """

    try:

        resultado = autenticar_y_configurar_respuesta(

            db=db,

            correo=formulario.username,

            contrasena=formulario.password,

            request=request,

            response=response,

        )


        return TokenResponse(

            access_token=resultado.access_token,

            token_type=resultado.token_type,

            expires_in=resultado.expires_in,

            refresh_token=None,

        )


    except CredencialesInvalidasError as exc:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail=str(exc),

            headers={

                "WWW-Authenticate": "Bearer",

            },

        ) from exc


    except DemasiadosIntentosLoginError as exc:

        raise HTTPException(

            status_code=status.HTTP_429_TOO_MANY_REQUESTS,

            detail=str(exc),

        ) from exc


    except (

        CuentaPendienteVerificacionError,

        CuentaBloqueadaError,

        CuentaInactivaError,

    ) as exc:

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail=str(exc),

        ) from exc


# ============================================================
# CONFIGURACIÓN PÚBLICA DE GOOGLE
# ============================================================

@router.get(
    "/google/config",
    status_code=status.HTTP_200_OK,
)
def obtener_configuracion_google() -> dict[str, str]:
    """
    Entrega al frontend el Client ID público utilizado por
    Google Identity Services.

    El Client ID identifica a la aplicación y no es un secreto.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "El acceso con Google todavía no está configurado."
            ),
        )

    return {
        "client_id": GOOGLE_CLIENT_ID,
    }


# ============================================================

# LOGIN CON GOOGLE

# ============================================================


@router.post(

    "/google",

    response_model=LoginResponse,

    status_code=status.HTTP_200_OK,

)

def login_google(

    datos: GoogleLoginRequest,

    request: Request,

    response: Response,

    db: DatabaseSession,

) -> LoginResponse:

    """

    Inicia sesión mediante una identidad verificada por Google.


    Google valida la identidad externa y posteriormente el sistema

    genera su propia sesión, access token y refresh token.

    """

    try:

        resultado = iniciar_sesion_google(

            db,

            credential=datos.credential,

            direccion_ip=obtener_direccion_ip(

                request

            ),

            user_agent=obtener_user_agent(

                request

            ),

        )


        if resultado.refresh_token is None:

            raise HTTPException(

                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

                detail=(

                    "No fue posible generar la sesión "

                    "de autenticación."

                ),

            )


        configurar_cookie_refresh(

            response,

            resultado.refresh_token,

        )


        return resultado.model_copy(

            update={

                "refresh_token": None,

            }

        )


    except GoogleNoConfiguradoError as exc:

        raise HTTPException(

            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,

            detail=str(exc),

        ) from exc


    except (

        GoogleTokenInvalidoError,

        GoogleCorreoNoVerificadoError,

    ) as exc:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail=str(exc),

        ) from exc


    except (

        GoogleCuentaBloqueadaError,

        GoogleCuentaInactivaError,

    ) as exc:

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail=str(exc),

        ) from exc


    except GoogleIdentidadEnConflictoError as exc:

        raise HTTPException(

            status_code=status.HTTP_409_CONFLICT,

            detail=str(exc),

        ) from exc


    except GoogleAuthServiceError as exc:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(exc),

        ) from exc


# ============================================================

# REFRESH TOKEN

# ============================================================


@router.post(

    "/refresh",

    response_model=TokenResponse,

    status_code=status.HTTP_200_OK,

)

def refrescar_token(

    request: Request,

    response: Response,

    db: DatabaseSession,

    datos: RefreshTokenRequest | None = Body(

        default=None

    ),

    refresh_cookie: str | None = Cookie(

        default=None,

        alias=REFRESH_TOKEN_COOKIE_NAME,

    ),

) -> TokenResponse:

    """

    Renueva el access token y rota el refresh token.

    """

    try:

        refresh_token = resolver_refresh_token(

            token_cookie=refresh_cookie,

            datos=datos,

        )


        resultado = renovar_sesion(

            db,

            refresh_token=refresh_token,

            direccion_ip=obtener_direccion_ip(request),

            user_agent=obtener_user_agent(request),

        )


        if resultado.refresh_token is None:

            raise HTTPException(

                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

                detail=(

                    "No fue posible renovar el refresh token."

                ),

            )


        configurar_cookie_refresh(

            response,

            resultado.refresh_token,

        )


        return TokenResponse(

            access_token=resultado.access_token,

            token_type=resultado.token_type,

            expires_in=resultado.expires_in,

            refresh_token=None,

        )


    except RefreshTokenInvalidoError as exc:

        eliminar_cookie_refresh(response)


        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail=str(exc),

            headers={

                "WWW-Authenticate": "Bearer",

            },

        ) from exc


# ============================================================

# LOGOUT

# ============================================================


@router.post(

    "/logout",

    response_model=MensajeResponse,

    status_code=status.HTTP_200_OK,

)

def logout(

    request: Request,

    response: Response,

    db: DatabaseSession,

    datos: RefreshTokenRequest | None = Body(

        default=None

    ),

    refresh_cookie: str | None = Cookie(

        default=None,

        alias=REFRESH_TOKEN_COOKIE_NAME,

    ),

) -> MensajeResponse:

    """

    Revoca la sesión asociada al refresh token.

    """

    refresh_token = resolver_refresh_token(

        token_cookie=refresh_cookie,

        datos=datos,

    )


    try:

        cerrar_sesion_por_refresh_token(

            db,

            refresh_token=refresh_token,

            direccion_ip=obtener_direccion_ip(request),

            user_agent=obtener_user_agent(request),

        )


    except (

        RefreshTokenInvalidoError,

        SesionYaRevocadaError,

    ):

        # El cierre es idempotente desde la perspectiva del

        # cliente: la cookie se elimina aunque la sesión ya no

        # exista o ya esté revocada.

        pass


    eliminar_cookie_refresh(response)


    return MensajeResponse(

        mensaje="La sesión fue cerrada correctamente."

    )


# ============================================================

# VERIFICACIÓN DE CORREO

# ============================================================


@router.post(

    "/verify-email",

    response_model=MensajeResponse,

    status_code=status.HTTP_200_OK,

)

def verificar_email(

    datos: CorreoVerificarRequest,

    request: Request,

    db: DatabaseSession,

) -> MensajeResponse:

    """

    Verifica un correo mediante el token recibido.

    """

    try:

        verificar_correo(

            db,

            token=datos.token.get_secret_value(),

            direccion_ip=obtener_direccion_ip(request),

            user_agent=obtener_user_agent(request),

        )


        return MensajeResponse(

            mensaje=(

                "El correo fue verificado correctamente. "

                "El acceso depende del estado de tu cuenta."

            )

        )


    except TokenVerificacionInvalidoError as exc:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(exc),

        ) from exc


    except CorreoYaVerificadoError as exc:

        raise HTTPException(

            status_code=status.HTTP_409_CONFLICT,

            detail=str(exc),

        ) from exc


    except CorreoNoEncontradoError as exc:

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail=str(exc),

        ) from exc


@router.post(

    "/resend-verification",

    response_model=MensajeResponse,

    status_code=status.HTTP_200_OK,

)

def reenviar_verificacion(

    datos: CorreoReenviarVerificacionRequest,

    request: Request,

    db: DatabaseSession,

) -> MensajeResponse:

    """

    Genera un nuevo token de verificación y vuelve a enviar

    el correo.

    """

    try:

        reenviar_verificacion_correo(

            db,

            correo=str(datos.correo),

            direccion_ip=obtener_direccion_ip(request),

            user_agent=obtener_user_agent(request),

        )

    except EnvioVerificacionCorreoError:

        # El servicio deja constancia del fallo SMTP. La respuesta pública no

        # distingue una cuenta pendiente de una inexistente o ya verificada.

        pass


    return MensajeResponse(

        mensaje=(

            "Si existe una cuenta pendiente asociada a ese correo, se enviará "

            "un nuevo enlace de verificación. Si solicitaste uno recientemente, "

            "espera antes de volver a intentarlo."

        )

    )


# ============================================================

# RECUPERACIÓN DE CONTRASEÑA

# ============================================================


@router.post(

    "/request-password-reset",

    response_model=MensajeResponse,

    status_code=status.HTTP_200_OK,

)

def solicitar_recuperacion(

    datos: SolicitudRecuperacionRequest,

    request: Request,

    db: DatabaseSession,

) -> MensajeResponse:

    """

    Solicita un enlace para restablecer la contraseña.


    La respuesta no revela si el correo está registrado.

    """

    try:

        solicitar_recuperacion_contrasena(

            db,

            correo=str(datos.correo),

            direccion_ip=obtener_direccion_ip(request),

            user_agent=obtener_user_agent(request),

        )


    except EnvioRecuperacionCorreoError:

        # Evitamos revelar que la cuenta existe. El evento

        # queda registrado en el backend.

        pass


    return MensajeResponse(

        mensaje=(

            "Si el correo está asociado a una cuenta válida, "

            "recibirás instrucciones para restablecer "

            "la contraseña."

        )

    )


@router.post(

    "/reset-password",

    response_model=MensajeResponse,

    status_code=status.HTTP_200_OK,

)

def restablecer_password(

    datos: RestablecerContrasenaRequest,

    request: Request,

    db: DatabaseSession,

) -> MensajeResponse:

    """

    Establece una nueva contraseña mediante un token temporal.

    """

    try:

        restablecer_contrasena(

            db,

            token=datos.token.get_secret_value(),

            nueva_contrasena=(

                datos.nueva_contrasena.get_secret_value()

            ),

            direccion_ip=obtener_direccion_ip(request),

            user_agent=obtener_user_agent(request),

        )


        return MensajeResponse(

            mensaje=(

                "La contraseña fue restablecida. "

                "Ya puedes iniciar sesión."

            )

        )


    except TokenRecuperacionInvalidoError as exc:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(exc),

        ) from exc


# ============================================================

# CAMBIO DE CONTRASEÑA AUTENTICADO

# ============================================================


@router.post(

    "/change-password",

    response_model=MensajeResponse,

    status_code=status.HTTP_200_OK,

)

def cambiar_password_autenticado(

    datos: CambioContrasenaRequest,

    request: Request,

    usuario: UsuarioActivo,

    db: DatabaseSession,

) -> MensajeResponse:

    """

    Cambia la contraseña del usuario autenticado.


    Por seguridad, las sesiones activas serán revocadas y el

    usuario deberá iniciar sesión nuevamente.

    """

    try:

        cambiar_contrasena(

            db,

            usuario=usuario,

            contrasena_actual=(

                datos.contrasena_actual.get_secret_value()

            ),

            nueva_contrasena=(

                datos.nueva_contrasena.get_secret_value()

            ),

            identificador_sesion_actual=None,

            direccion_ip=obtener_direccion_ip(request),

            user_agent=obtener_user_agent(request),

        )


        return MensajeResponse(

            mensaje=(

                "La contraseña fue cambiada correctamente. "

                "Debes iniciar sesión nuevamente."

            )

        )


    except ContrasenaActualInvalidaError as exc:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(exc),

        ) from exc
