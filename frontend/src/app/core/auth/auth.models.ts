import {
  UsuarioAutenticadoResponse,
} from '../account/account.models';


// ============================================================
// REGISTRO
// ============================================================

export interface RegistroRequest {
  nombres: string;
  apellidos: string;
  correo: string;
  contrasena: string;
  confirmar_contrasena: string;
}


// ============================================================
// LOGIN TRADICIONAL
// ============================================================

export interface LoginRequest {
  correo: string;
  contrasena: string;
}


// ============================================================
// LOGIN CON GOOGLE
// ============================================================

export interface GoogleLoginRequest {
  credential: string;
}


// ============================================================
// REFRESH
// ============================================================

export interface RefreshTokenRequest {
  refresh_token?: string | null;
}


// ============================================================
// CAMBIO DE CONTRASEÑA
// ============================================================

export interface CambioContrasenaRequest {
  contrasena_actual: string;
  nueva_contrasena: string;
  confirmar_nueva_contrasena: string;
}


// ============================================================
// RECUPERACIÓN
// ============================================================

export interface SolicitudRecuperacionRequest {
  correo: string;
}


export interface RestablecerContrasenaRequest {
  token: string;
  nueva_contrasena: string;
  confirmar_nueva_contrasena: string;
}


// ============================================================
// VERIFICACIÓN DE CORREO
// ============================================================

export interface CorreoVerificarRequest {
  token: string;
}


export interface CorreoReenviarVerificacionRequest {
  correo: string;
}


// ============================================================
// RESPUESTAS
// ============================================================

export interface MensajeResponse {
  mensaje: string;
}


export interface RegistroResponse {
  id_usuario: number;
  correo: string;
  estado: string;
  requiere_verificacion: boolean;
  mensaje: string;
}


export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string | null;
}


export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string | null;
  usuario: UsuarioAutenticadoResponse;
}