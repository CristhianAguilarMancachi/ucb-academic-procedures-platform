import { inject } from '@angular/core';
import {
  CanActivateFn,
  Router,
} from '@angular/router';

import {
  catchError,
  map,
  of,
} from 'rxjs';

import { AuthService } from './auth.service';


export const authGuard: CanActivateFn = (
  route,
  state,
) => {

  const authService = inject(AuthService);
  const router = inject(Router);


  if (authService.autenticado()) {
    return true;
  }


  return authService.restaurarSesion().pipe(

    map((sesionRestaurada) => {

      if (sesionRestaurada) {
        return true;
      }

      return router.createUrlTree(
        ['/login'],
        {
          queryParams: {
            returnUrl: state.url,
          },
        },
      );
    }),

    catchError(() => {
      return of(
        router.createUrlTree(
          ['/login'],
          {
            queryParams: {
              returnUrl: state.url,
            },
          },
        ),
      );
    }),
  );
};