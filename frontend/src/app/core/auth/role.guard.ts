import { inject } from '@angular/core';

import {
  CanActivateFn,
  Router,
} from '@angular/router';

import {
  map,
} from 'rxjs';

import {
  AuthService,
} from './auth.service';


export const roleGuard: CanActivateFn = (
  route,
  state,
) => {

  const authService =
    inject(AuthService);

  const router =
    inject(Router);

  const rolesRequeridos =
    route.data?.['roles'] as string[] | undefined;


  if (
    !rolesRequeridos
    || rolesRequeridos.length === 0
  ) {
    return true;
  }


  if (authService.autenticado()) {

    if (
      authService.tieneAlgunoDeLosRoles(
        rolesRequeridos,
      )
    ) {
      return true;
    }

    return router.createUrlTree([
      '/',
    ]);
  }


  return authService
    .restaurarSesion()
    .pipe(

      map((restaurada) => {

        if (!restaurada) {

          return router.createUrlTree(
            ['/login'],
            {
              queryParams: {
                returnUrl: state.url,
              },
            },
          );
        }


        if (
          authService.tieneAlgunoDeLosRoles(
            rolesRequeridos,
          )
        ) {
          return true;
        }


        return router.createUrlTree([
          '/',
        ]);
      }),

    );
};