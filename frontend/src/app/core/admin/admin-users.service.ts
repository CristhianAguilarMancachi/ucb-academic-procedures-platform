import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import {
  ListaRolesResponse,
  ListaUsuariosParams,
  ListaUsuariosResponse,
  RolAsignarRequest,
  RolRevocarRequest,
  UsuarioAdministradorDetalleResponse,
  UsuarioEstadoActualizarRequest,
  UsuarioRolResponse,
} from './admin.models';


@Injectable({
  providedIn: 'root',
})
export class AdminUsersService {

  private readonly http = inject(HttpClient);

  private readonly apiUrl =
    '/api/admin/users';


  listarUsuarios(
    filtros: ListaUsuariosParams = {},
  ): Observable<ListaUsuariosResponse> {

    let params = new HttpParams();
    if (filtros.id_rol) params = params.set('id_rol', filtros.id_rol);

    if (filtros.pagina !== undefined) {
      params = params.set(
        'pagina',
        filtros.pagina.toString(),
      );
    }

    if (filtros.por_pagina !== undefined) {
      params = params.set(
        'por_pagina',
        filtros.por_pagina.toString(),
      );
    }

    if (filtros.estado) {
      params = params.set(
        'estado',
        filtros.estado,
      );
    }

    if (filtros.busqueda?.trim()) {
      params = params.set(
        'busqueda',
        filtros.busqueda.trim(),
      );
    }

    return this.http.get<ListaUsuariosResponse>(
      this.apiUrl,
      {
        params,
      },
    );
  }


  obtenerUsuario(
    idUsuario: number,
  ): Observable<UsuarioAdministradorDetalleResponse> {

    return this.http.get<UsuarioAdministradorDetalleResponse>(
      `${this.apiUrl}/${idUsuario}`,
    );
  }


  cambiarEstado(
    idUsuario: number,
    datos: UsuarioEstadoActualizarRequest,
  ): Observable<UsuarioAdministradorDetalleResponse> {

    return this.http.patch<UsuarioAdministradorDetalleResponse>(
      `${this.apiUrl}/${idUsuario}/status`,
      datos,
    );
  }


  obtenerRoles(): Observable<ListaRolesResponse> {

    return this.http.get<ListaRolesResponse>(
      `${this.apiUrl}/catalog/roles`,
    );
  }


  asignarRol(
    idUsuario: number,
    datos: RolAsignarRequest,
  ): Observable<UsuarioRolResponse> {

    return this.http.post<UsuarioRolResponse>(
      `${this.apiUrl}/${idUsuario}/roles`,
      datos,
    );
  }


  revocarRol(
    idUsuario: number,
    idRol: number,
    datos: RolRevocarRequest = {},
  ): Observable<UsuarioRolResponse> {

    return this.http.delete<UsuarioRolResponse>(
      `${this.apiUrl}/${idUsuario}/roles/${idRol}`,
      {
        body: datos,
      },
    );
  }
}