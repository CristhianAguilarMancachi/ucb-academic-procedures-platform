import { Routes } from '@angular/router';

import { MainLayout } from './core/layout/main-layout/main-layout';

import { RagHome } from './features/rag/pages/rag-home/rag-home';

import { LoginComponent } from './features/auth/login/login.component';
import { RegisterComponent } from './features/auth/register/register.component';
import { VerifyEmailComponent } from './features/auth/verify-email/verify-email.component';
import { ForgotPasswordComponent } from './features/auth/forgot-password/forgot-password.component';
import { ResetPasswordComponent } from './features/auth/reset-password/reset-password.component';

import { ProfileComponent } from './features/account/profile/profile.component';
import { ChangePasswordComponent } from './features/account/change-password/change-password.component';

import { UserListComponent } from './features/admin/users/user-list/user-list.component';
import { UserDetailComponent } from './features/admin/users/user-detail/user-detail.component';

import { authGuard } from './core/auth/auth.guard';
import { roleGuard } from './core/auth/role.guard';

export const routes: Routes = [
  // =========================================================
  // AUTENTICACIÓN
  // =========================================================

  {
    path: 'login',
    component: LoginComponent,
  },

  {
    path: 'registro',
    component: RegisterComponent,
  },

  {
    path: 'verificar-correo',
    component: VerifyEmailComponent,
  },

  {
    path: 'recuperar-contrasena',
    component: ForgotPasswordComponent,
  },

  {
    path: 'restablecer-contrasena',
    component: ResetPasswordComponent,
  },

  // =========================================================
  // APLICACIÓN
  // =========================================================

  {
    path: '',
    component: MainLayout,

    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'informacion',
      },

      // Módulo informativo
      {
        path: 'informacion',
        component: RagHome,
      },

      // Gestión y seguimiento de trámites
      { path: 'tramites/nuevo', pathMatch: 'full', redirectTo: 'tramites' },
      {
        path: 'tramites',
        loadComponent: () =>
          import('./features/gestion-seguimiento/pages/tramites-disponibles/tramites-disponibles.component').then(
            (m) => m.TramitesDisponiblesComponent,
          ),
      },
      {
        path: 'tramites/:id',
        loadComponent: () =>
          import('./features/gestion-seguimiento/pages/tramites-disponibles/tramites-disponibles.component').then(
            (m) => m.TramitesDisponiblesComponent,
          ),
      },
      {
        path: 'mis-solicitudes',
        canActivate: [authGuard, roleGuard],
        data: { roles: ['solicitante', 'administrador'] },
        loadComponent: () =>
          import('./features/gestion-seguimiento/pages/lista-solicitudes/lista-solicitudes.component').then(
            (m) => m.ListaSolicitudesComponent,
          ),
      },
      {
        path: 'solicitudes/:id/preparar',
        canActivate: [authGuard, roleGuard],
        data: { roles: ['solicitante', 'administrador'] },
        loadComponent: () =>
          import('./features/gestion-seguimiento/pages/nueva-solicitud/nueva-solicitud.component').then(
            (m) => m.NuevaSolicitudComponent,
          ),
      },
      {
        path: 'solicitudes/:id',
        canActivate: [authGuard, roleGuard],
        data: { roles: ['solicitante', 'administrador'] },
        loadComponent: () =>
          import('./features/gestion-seguimiento/pages/seguimiento-solicitud/seguimiento-solicitud.component').then(
            (m) => m.SeguimientoSolicitudComponent,
          ),
      },
      {
        path: 'admin/solicitudes',
        canActivate: [authGuard, roleGuard],
        data: { roles: ['personal_administrativo', 'administrador'], admin: true },
        loadComponent: () =>
          import('./features/gestion-seguimiento/pages/lista-solicitudes/lista-solicitudes.component').then(
            (m) => m.ListaSolicitudesComponent,
          ),
      },
      {
        path: 'admin/solicitudes/:id',
        canActivate: [authGuard, roleGuard],
        data: { roles: ['personal_administrativo', 'administrador'], admin: true },
        loadComponent: () =>
          import('./features/gestion-seguimiento/pages/seguimiento-solicitud/seguimiento-solicitud.component').then(
            (m) => m.SeguimientoSolicitudComponent,
          ),
      },
      {
        path: 'admin/tramites',
        canActivate: [authGuard, roleGuard],
        data: { roles: ['administrador'] },
        loadComponent: () =>
          import('./features/gestion-seguimiento/pages/configuracion-tramites/configuracion-tramites.component').then(
            (m) => m.ConfiguracionTramitesComponent,
          ),
      },

      // Cuenta
      {
        path: 'perfil',
        component: ProfileComponent,
        canActivate: [authGuard],
      },

      {
        path: 'cambiar-contrasena',
        component: ChangePasswordComponent,
        canActivate: [authGuard],
      },

      // Administración
      {
        path: 'admin/usuarios',
        component: UserListComponent,
        canActivate: [authGuard, roleGuard],
        data: {
          roles: ['administrador'],
        },
      },

      {
        path: 'admin/usuarios/:id',
        component: UserDetailComponent,
        canActivate: [authGuard, roleGuard],
        data: {
          roles: ['administrador'],
        },
      },
    ],
  },

  // =========================================================
  // FALLBACK
  // =========================================================

  {
    path: '**',
    redirectTo: 'informacion',
  },
];
