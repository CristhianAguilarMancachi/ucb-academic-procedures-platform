import {
  UsuarioAutenticadoResponse,
} from '../account/account.models';


export interface RegistroRequest {
  nombres: string;
  apellidos: string;
  correo: string;
  contrasena: string;
  confirmar_contrasena: string;
}


export interface LoginRequest {
  correo: string;
  contrasena: string;
}


export interface RefreshTokenRequest {
  refresh_token?: string | null;
}


export interface CambioContrasenaRequest {
  contrasena_actual: string;
  nueva_contrasena: string;
  confirmar_nueva_contrasena: string;
}


export interface SolicitudRecuperacionRequest {
  correo: string;
}


export interface RestablecerContrasenaRequest {
  token: string;
  nueva_contrasena: string;
  confirmar_nueva_contrasena: string;
}


export interface CorreoVerificarRequest {
  token: string;
}


export interface CorreoReenviarVerificacionRequest {
  correo: string;
}


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