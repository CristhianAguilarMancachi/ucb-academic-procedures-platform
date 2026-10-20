
import { inject } from '@angular/core';

import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandlerFn,
  HttpInterceptorFn,
  HttpRequest,
} from '@angular/common/http';

import {
  Observable,
  catchError,
  switchMap,
  throwError,
} from 'rxjs';

import { AuthService } from './auth.service';

const RUTAS_SIN_BEARER = [
  '/api/auth/register',
  '/api/auth/login',
  '/api/auth/token',
  '/api/auth/refresh',
  '/api/auth/logout',
  '/api/auth/verify-email',
  '/api/auth/resend-verification',
  '/api/auth/request-password-reset',
  '/api/auth/reset-password',
];

function requiereBearer(
  url: string,
): boolean {
  return !RUTAS_SIN_BEARER.some(
    (ruta) => url.includes(ruta),
  );
}

function agregarBearer(
  request: HttpRequest<unknown>,
  token: string,
): HttpRequest<unknown> {
  return request.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export const authInterceptor: HttpInterceptorFn = (
  request,
  next,
): Observable<HttpEvent<unknown>> => {

  const authService = inject(AuthService);

  const requiereAutenticacion = requiereBearer(request.url);
  const tokenOriginal = authService.obtenerAccessToken();

  const requestInicial = (
    requiereAutenticacion && tokenOriginal !== null
  )
    ? agregarBearer(request, tokenOriginal)
    : request;

  return next(requestInicial).pipe(
    catchError((error: HttpErrorResponse) => {
      if (
        !(error instanceof HttpErrorResponse)
        || error.status !== 401
        || !requiereAutenticacion
      ) {
        return throwError(() => error);
      }

      const tokenActual = authService.obtenerAccessToken();

      // Si otra petición ya renovó el token, no rotamos
      // nuevamente la cookie: reutilizamos el token nuevo.
      if (
        tokenOriginal !== null
        && tokenActual !== null
        && tokenActual !== tokenOriginal
      ) {
        return next(
          agregarBearer(request, tokenActual),
        );
      }

      // refresh() comparte una única operación en curso.
      // Si falla la renovación, la sesión deja de ser válida.
      return authService.refresh().pipe(
        catchError((refreshError) => {
          authService.limpiarSesion();
          return throwError(() => refreshError);
        }),

        switchMap((respuesta) => {
          return next(
            agregarBearer(
              request,
              respuesta.access_token,
            ),
          );
        }),
      );
    }),
  );
};
