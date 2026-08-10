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

  const token = authService.obtenerAccessToken();

  let requestAutenticada = request;


  if (
    token !== null
    && requiereBearer(request.url)
  ) {
    requestAutenticada = agregarBearer(
      request,
      token,
    );
  }


  return next(requestAutenticada).pipe(

    catchError((error: HttpErrorResponse) => {

      /*
       * Solo intentamos renovar la sesión cuando:
       *
       * 1. El backend respondió 401.
       * 2. La petición necesitaba autenticación.
       * 3. No estamos ya intentando un refresh.
       */

      if (
        error.status !== 401
        || !requiereBearer(request.url)
      ) {
        return throwError(
          () => error,
        );
      }


      return authService.refresh().pipe(

        switchMap((respuesta) => {

          const nuevaRequest = agregarBearer(
            request,
            respuesta.access_token,
          );

          return next(nuevaRequest);
        }),

        catchError((refreshError) => {

          authService.limpiarSesion();

          return throwError(
            () => refreshError,
          );
        }),
      );
    }),
  );
};