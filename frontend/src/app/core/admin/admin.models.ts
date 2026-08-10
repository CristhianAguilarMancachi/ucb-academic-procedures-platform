import {
  RolResponse,
  UsuarioAutenticadoResponse,
} from '../account/account.models';


export type EstadoUsuarioAdministracion =
  | 'pendiente_verificacion'
  | 'activo'
  | 'bloqueado'
  | 'inactivo';


export interface UsuarioResumenResponse {
  id_usuario: number;
  nombres: string;
  apellidos: string;
  estado: EstadoUsuarioAdministracion;
  fecha_ultimo_acceso: string | null;
  fecha_creacion: string;
}


export interface ListaUsuariosResponse {
  items: UsuarioResumenResponse[];
  total: number;
  pagina: number;
  por_pagina: number;
}


export interface ListaUsuariosParams {
  pagina?: number;
  por_pagina?: number;
  estado?: EstadoUsuarioAdministracion;
  busqueda?: string;
}


export interface UsuarioAdministradorDetalleResponse
  extends UsuarioAutenticadoResponse {
}


export interface UsuarioEstadoActualizarRequest {
  estado: EstadoUsuarioAdministracion;
  motivo?: string | null;
}


export interface ListaRolesResponse {
  items: RolResponse[];
  total: number;
}


export interface RolAsignarRequest {
  id_rol: number;
}


export interface RolRevocarRequest {
  motivo?: string | null;
}


export interface UsuarioRolResponse {
  id_usuario_rol: number;
  id_usuario: number;
  id_rol: number;
  activo: boolean;
  asignado_por: number | null;
  fecha_asignacion: string;
  fecha_revocacion: string | null;
}