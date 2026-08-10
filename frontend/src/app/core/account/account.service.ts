import { Injectable, inject } from '@angular/core';
import {
  HttpClient,
  HttpParams,
} from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  CerrarTodasSesionesRequest,
  CerrarTodasSesionesResponse,
  ListaSesionesResponse,
  SesionRevocarRequest,
  SesionRevocarResponse,
  UsuarioActualizarRequest,
  UsuarioAutenticadoResponse,
} from './account.models';


@Injectable({
  providedIn: 'root',
})
export class AccountService {

  private readonly http = inject(HttpClient);

  private readonly apiUrl = '/api/users';


  obtenerPerfil(): Observable<UsuarioAutenticadoResponse> {
    return this.http.get<UsuarioAutenticadoResponse>(
      `${this.apiUrl}/me`,
    );
  }


  actualizarPerfil(
    datos: UsuarioActualizarRequest,
  ): Observable<UsuarioAutenticadoResponse> {
    return this.http.patch<UsuarioAutenticadoResponse>(
      `${this.apiUrl}/me`,
      datos,
    );
  }


  obtenerSesiones(
    soloVigentes = false,
  ): Observable<ListaSesionesResponse> {
    const params = new HttpParams().set(
      'solo_vigentes',
      soloVigentes,
    );

    return this.http.get<ListaSesionesResponse>(
      `${this.apiUrl}/me/sessions`,
      {
        params,
      },
    );
  }


  cerrarSesion(
    idSesion: number,
    datos?: SesionRevocarRequest,
  ): Observable<SesionRevocarResponse> {
    return this.http.delete<SesionRevocarResponse>(
      `${this.apiUrl}/me/sessions/${idSesion}`,
      {
        body: datos ?? null,
      },
    );
  }


  cerrarTodasLasSesiones(
    datos: CerrarTodasSesionesRequest = {
      conservar_sesion_actual: false,
    },
  ): Observable<CerrarTodasSesionesResponse> {
    return this.http.delete<CerrarTodasSesionesResponse>(
      `${this.apiUrl}/me/sessions`,
      {
        body: datos,
      },
    );
  }
}