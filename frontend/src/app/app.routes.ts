import { Routes } from '@angular/router';

import { MainLayout } from './core/layout/main-layout/main-layout';

import { RagHome } from './features/rag/pages/rag-home/rag-home';

import { LoginComponent } from './features/auth/login/login.component';
import { RegisterComponent } from './features/auth/register/register.component';
import { VerifyEmailComponent } from './features/auth/verify-email/verify-email.component';
import { ForgotPasswordComponent } from './features/auth/forgot-password/forgot-password.component';
import { ResetPasswordComponent } from './features/auth/reset-password/reset-password.component';

import { ProfileComponent } from './features/account/profile/profile.component';
import { SessionsComponent } from './features/account/sessions/sessions.component';
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

      // Cuenta
      {
        path: 'perfil',
        component: ProfileComponent,
        canActivate: [
          authGuard,
        ],
      },

      {
        path: 'sesiones',
        component: SessionsComponent,
        canActivate: [
          authGuard,
        ],
      },

      {
        path: 'cambiar-contrasena',
        component: ChangePasswordComponent,
        canActivate: [
          authGuard,
        ],
      },

      // Administración
      {
        path: 'admin/usuarios',
        component: UserListComponent,
        canActivate: [
          authGuard,
          roleGuard,
        ],
        data: {
          roles: [
            'administrador',
          ],
        },
      },

      {
        path: 'admin/usuarios/:id',
        component: UserDetailComponent,
        canActivate: [
          authGuard,
          roleGuard,
        ],
        data: {
          roles: [
            'administrador',
          ],
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