
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import {
  Observable,
  catchError,
  finalize,
  map,
  of,
  shareReplay,
  switchMap,
  tap,
  throwError,
} from 'rxjs';

import {
  UsuarioAutenticadoResponse,
} from '../account/account.models';

import {
  CambioContrasenaRequest,
  CorreoReenviarVerificacionRequest,
  CorreoVerificarRequest,
  GoogleLoginRequest,
  LoginRequest,
  LoginResponse,
  MensajeResponse,
  RegistroRequest,
  RegistroResponse,
  RestablecerContrasenaRequest,
  SolicitudRecuperacionRequest,
  TokenResponse,
} from './auth.models';

@Injectable({
  providedIn: 'root',
})
export class AuthService {

  private readonly http = inject(HttpClient);

  private readonly apiAuthUrl = '/api/auth';
  private readonly apiUsersUrl = '/api/users';

  private accessToken: string | null = null;

  // Compartimos las operaciones simultáneas para evitar
  // múltiples rotaciones del mismo refresh token.
  private refreshEnCurso$: Observable<TokenResponse> | null = null;
  private restauracionEnCurso$: Observable<boolean> | null = null;

  readonly usuarioActual = signal<
    UsuarioAutenticadoResponse | null
  >(null);

  readonly autenticado = signal(false);
  readonly sesionInicializada = signal(false);

  // =========================================================
  // ACCESS TOKEN
  // =========================================================

  obtenerAccessToken(): string | null {
    return this.accessToken;
  }

  establecerAccessToken(
    token: string | null,
  ): void {
    this.accessToken = token;
  }

  // =========================================================
  // REGISTRO
  // =========================================================

  registrar(
    datos: RegistroRequest,
  ): Observable<RegistroResponse> {
    return this.http.post<RegistroResponse>(
      `${this.apiAuthUrl}/register`,
      datos,
    );
  }

  // =========================================================
  // ESTABLECER SESIÓN AUTENTICADA
  // =========================================================

  private establecerSesion(
    respuesta: LoginResponse,
  ): void {
    this.accessToken = respuesta.access_token;
    this.usuarioActual.set(respuesta.usuario);
    this.autenticado.set(true);
    this.sesionInicializada.set(true);
  }

  // =========================================================
  // LOGIN TRADICIONAL
  // =========================================================

  login(
    datos: LoginRequest,
  ): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(
      `${this.apiAuthUrl}/login`,
      datos,
      {
        withCredentials: true,
      },
    ).pipe(
      tap((respuesta) => {
        this.establecerSesion(respuesta);
      }),
    );
  }

  // =========================================================
  // LOGIN CON GOOGLE
  // =========================================================

  loginGoogle(
    credential: string,
  ): Observable<LoginResponse> {
    const datos: GoogleLoginRequest = {
      credential,
    };

    return this.http.post<LoginResponse>(
      `${this.apiAuthUrl}/google`,
      datos,
      {
        withCredentials: true,
      },
    ).pipe(
      tap((respuesta) => {
        this.establecerSesion(respuesta);
      }),
    );
  }

  // =========================================================
  // REFRESH TOKEN
  // =========================================================

  refresh(): Observable<TokenResponse> {
    if (this.refreshEnCurso$ !== null) {
      return this.refreshEnCurso$;
    }

    const operacion$ = this.http.post<TokenResponse>(
      `${this.apiAuthUrl}/refresh`,
      {},
      {
        withCredentials: true,
      },
    ).pipe(
      tap((respuesta) => {
        this.accessToken = respuesta.access_token;
      }),
      finalize(() => {
        this.refreshEnCurso$ = null;
      }),
      shareReplay({
        bufferSize: 1,
        refCount: false,
      }),
    );

    this.refreshEnCurso$ = operacion$;
    return operacion$;
  }

  // =========================================================
  // RECUPERACIÓN DE SESIÓN
  // =========================================================

  restaurarSesion(): Observable<boolean> {
    if (this.autenticado()) {
      this.sesionInicializada.set(true);
      return of(true);
    }

    // Si un guard o el layout ya está restaurando,
    // todos esperan el mismo resultado.
    if (this.restauracionEnCurso$ !== null) {
      return this.restauracionEnCurso$;
    }

    const operacion$ = this.refresh().pipe(
      switchMap(() => this.obtenerUsuarioActual()),

      tap((usuario) => {
        this.usuarioActual.set(usuario);
        this.autenticado.set(true);
      }),

      map(() => true),

      catchError(() => {
        this.limpiarSesion();
        return of(false);
      }),

      finalize(() => {
        this.sesionInicializada.set(true);
        this.restauracionEnCurso$ = null;
      }),

      shareReplay({
        bufferSize: 1,
        refCount: false,
      }),
    );

    this.restauracionEnCurso$ = operacion$;
    return operacion$;
  }

  private obtenerUsuarioActual():
    Observable<UsuarioAutenticadoResponse> {
    return this.http.get<UsuarioAutenticadoResponse>(
      `${this.apiUsersUrl}/me`,
    );
  }

  // =========================================================
  // LOGOUT
  // =========================================================

  logout(): Observable<MensajeResponse> {
    return this.http.post<MensajeResponse>(
      `${this.apiAuthUrl}/logout`,
      {},
      {
        withCredentials: true,
      },
    ).pipe(
      tap(() => {
        this.limpiarSesion();
      }),

      catchError((error) => {
        this.limpiarSesion();
        return throwError(() => error);
      }),
    );
  }

  limpiarSesion(): void {
    this.accessToken = null;
    this.usuarioActual.set(null);
    this.autenticado.set(false);
  }

  // =========================================================
  // VERIFICACIÓN DE CORREO
  // =========================================================

  verificarCorreo(
    token: string,
  ): Observable<MensajeResponse> {
    const datos: CorreoVerificarRequest = {
      token,
    };

    return this.http.post<MensajeResponse>(
      `${this.apiAuthUrl}/verify-email`,
      datos,
    );
  }

  reenviarVerificacion(
    correo: string,
  ): Observable<MensajeResponse> {
    const datos: CorreoReenviarVerificacionRequest = {
      correo,
    };

    return this.http.post<MensajeResponse>(
      `${this.apiAuthUrl}/resend-verification`,
      datos,
    );
  }

  // =========================================================
  // RECUPERACIÓN DE CONTRASEÑA
  // =========================================================

  solicitarRecuperacion(
    correo: string,
  ): Observable<MensajeResponse> {
    const datos: SolicitudRecuperacionRequest = {
      correo,
    };

    return this.http.post<MensajeResponse>(
      `${this.apiAuthUrl}/request-password-reset`,
      datos,
    );
  }

  restablecerContrasena(
    datos: RestablecerContrasenaRequest,
  ): Observable<MensajeResponse> {
    return this.http.post<MensajeResponse>(
      `${this.apiAuthUrl}/reset-password`,
      datos,
    );
  }

  // =========================================================
  // CAMBIO DE CONTRASEÑA
  // =========================================================

  cambiarContrasena(
    datos: CambioContrasenaRequest,
  ): Observable<MensajeResponse> {
    return this.http.post<MensajeResponse>(
      `${this.apiAuthUrl}/change-password`,
      datos,
    ).pipe(
      tap(() => {
        this.limpiarSesion();
      }),
    );
  }

  // =========================================================
  // ROLES
  // =========================================================

  tieneRol(
    rol: string,
  ): boolean {
    const usuario = this.usuarioActual();

    if (usuario === null) {
      return false;
    }

    return usuario.roles.some(
      (item) => item.nombre === rol,
    );
  }

  tieneAlgunoDeLosRoles(
    rolesPermitidos: string[],
  ): boolean {
    return rolesPermitidos.some(
      (rol) => this.tieneRol(rol),
    );
  }

  // =========================================================
  // IDENTIFICADOR DE SESIÓN
  // =========================================================

  obtenerIdentificadorSesionActual(): string | null {
    if (!this.accessToken) {
      return null;
    }

    try {
      const partes = this.accessToken.split('.');

      if (partes.length !== 3) {
        return null;
      }

      let payloadBase64 = partes[1]
        .replace(/-/g, '+')
        .replace(/_/g, '/');

      while (payloadBase64.length % 4 !== 0) {
        payloadBase64 += '=';
      }

      const payload = JSON.parse(
        atob(payloadBase64),
      ) as {
        session_id?: string;
      };

      return payload.session_id ?? null;

    } catch {
      return null;
    }
  }
}
