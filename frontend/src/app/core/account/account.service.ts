import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
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
}
