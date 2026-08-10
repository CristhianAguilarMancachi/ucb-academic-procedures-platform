export type EstadoUsuario =
  | 'pendiente_verificacion'
  | 'activo'
  | 'bloqueado'
  | 'inactivo';

export type TipoCorreo =
  | 'institucional'
  | 'personal';


export interface CorreoResponse {
  id_usuario_correo: number;
  correo: string;
  tipo: TipoCorreo;
  es_principal: boolean;
  verificado: boolean;
  activo: boolean;
  fecha_verificacion: string | null;
  fecha_creacion: string;
}


export interface RolResponse {
  id_rol: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
}


export interface UsuarioResponse {
  id_usuario: number;
  nombres: string;
  apellidos: string;
  estado: EstadoUsuario;
  fecha_ultimo_acceso: string | null;
  fecha_creacion: string;
  fecha_actualizacion: string;
}


export interface UsuarioAutenticadoResponse
  extends UsuarioResponse {

  correos: CorreoResponse[];
  roles: RolResponse[];
}


export interface UsuarioActualizarRequest {
  nombres?: string | null;
  apellidos?: string | null;
}


export interface SesionResumenResponse {
  id_sesion: number;
  identificador_sesion: string;

  fecha_creacion: string;
  fecha_ultima_actividad: string;
  fecha_expiracion: string;
  fecha_revocacion: string | null;

  direccion_ip: string | null;
  user_agent: string | null;
}


export interface ListaSesionesResponse {
  items: SesionResumenResponse[];
  total: number;
}


export interface SesionRevocarRequest {
  motivo?: string | null;
}


export interface SesionRevocarResponse {
  id_sesion: number;
  identificador_sesion: string;
  fecha_revocacion: string;
  mensaje: string;
}


export interface CerrarTodasSesionesRequest {
  conservar_sesion_actual: boolean;
}


export interface CerrarTodasSesionesResponse {
  sesiones_revocadas: number;
  sesion_actual_conservada: boolean;
  mensaje: string;
}