import {
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';

import {
  NgFor,
  NgIf,
  NgSwitch,
  NgSwitchCase,
} from '@angular/common';

import {
  Router,
  RouterLink,
  RouterLinkActive,
} from '@angular/router';

import {
  NgIcon,
  provideIcons,
} from '@ng-icons/core';

import {
  heroPlusCircle,
  heroFolderOpen,
  heroSparkles,
  heroUserCircle,
  heroChevronUp,
  heroArrowRightOnRectangle,
  heroLockClosed,
} from '@ng-icons/heroicons/outline';

import {
  SIDEBAR_MENU,
} from '../../../core/config/sidebar-menu.config';

import {
  MenuItem,
} from '../../models/menu-item.model';

import {
  AuthService,
} from '../../../core/auth/auth.service';


interface MenuSection {
  nombre: string;

  items: MenuItem[];
}


@Component({
  selector:
    'app-app-sidebar',

  imports: [
    NgFor,
    NgIf,
    NgSwitch,
    NgSwitchCase,
    RouterLink,
    RouterLinkActive,
    NgIcon,
  ],

  providers: [
    provideIcons({
      heroPlusCircle,
      heroFolderOpen,
      heroSparkles,
      heroUserCircle,
      heroChevronUp,
      heroArrowRightOnRectangle,
      heroLockClosed,
    }),
  ],

  templateUrl:
    './app-sidebar.html',

  styleUrl:
    './app-sidebar.scss',
})
export class AppSidebar {

  readonly authService =
    inject(AuthService);

  private readonly router =
    inject(Router);


  readonly menuCuentaAbierto =
    signal(false);

  readonly cerrandoSesion =
    signal(false);


  readonly exactRouteOptions = {
    exact: true,
  };


  readonly menuSections =
    computed<MenuSection[]>(
      () => {

        const secciones =
          new Map<
            string,
            MenuItem[]
          >();


        for (
          const item
          of SIDEBAR_MENU
        ) {

          if (
            !this.puedeVer(
              item,
            )
          ) {
            continue;
          }


          const nombre =
            item.section
            ?? 'GENERAL';


          const items =
            secciones.get(
              nombre,
            );


          if (items) {

            items.push(
              item,
            );

          } else {

            secciones.set(
              nombre,
              [item],
            );
          }
        }


        return Array
          .from(
            secciones.entries(),
          )
          .map(
            ([
              nombre,
              items,
            ]) => ({
              nombre,
              items,
            }),
          );
      },
    );


  readonly nombreUsuario =
    computed(
      () => {

        const usuario =
          this.authService
            .usuarioActual();


        if (!usuario) {
          return '';
        }


        return [
          usuario.nombres,
          usuario.apellidos,
        ]
          .filter(Boolean)
          .join(' ')
          .trim();
      },
    );


  readonly inicialUsuario =
    computed(
      () => {

        const nombre =
          this.nombreUsuario();


        if (!nombre) {
          return 'U';
        }


        return nombre
          .charAt(0)
          .toUpperCase();
      },
    );


  readonly rolUsuario =
    computed(
      () => {

        const usuario =
          this.authService
            .usuarioActual();


        const rol =
          usuario?.roles
            ?.find(
              item =>
                item.activo,
            );


        if (!rol) {
          return '';
        }


        switch (
          rol.nombre
        ) {

          case 'solicitante':
            return 'Solicitante';

          case 'personal_administrativo':
            return 'Personal administrativo';

          case 'administrador':
            return 'Administrador';

          default:
            return rol.nombre;
        }
      },
    );


  alternarMenuCuenta():
    void {

    this.menuCuentaAbierto
      .update(
        abierto =>
          !abierto,
      );
  }


  cerrarMenuCuenta():
    void {

    this.menuCuentaAbierto
      .set(false);
  }


  irAIniciarSesion():
    void {

    this.cerrarMenuCuenta();

    this.router
      .navigate([
        '/login',
      ]);
  }


  irAPerfil():
    void {

    this.cerrarMenuCuenta();

    this.router
      .navigate([
        '/perfil',
      ]);
  }


  irASeguridad():
    void {

    this.cerrarMenuCuenta();

    this.router
      .navigate([
        '/cambiar-contrasena',
      ]);
  }


  cerrarSesion():
    void {

    if (
      this.cerrandoSesion()
    ) {
      return;
    }


    this.cerrandoSesion
      .set(true);


    this.authService
      .logout()
      .subscribe({

        next: () => {

          this.cerrandoSesion
            .set(false);

          this.cerrarMenuCuenta();

          this.router
            .navigate([
              '/login',
            ]);
        },

        error: () => {

          this.cerrandoSesion
            .set(false);

          this.cerrarMenuCuenta();

          this.router
            .navigate([
              '/login',
            ]);
        },
      });
  }


  private puedeVer(
    item: MenuItem,
  ): boolean {

    if (
      item.requiresAuth
      && !this.authService
        .autenticado()
    ) {
      return false;
    }


    if (
      item.roles
      && item.roles.length > 0
      && !this.authService
        .tieneAlgunoDeLosRoles(
          item.roles,
        )
    ) {
      return false;
    }


    return true;
  }
}