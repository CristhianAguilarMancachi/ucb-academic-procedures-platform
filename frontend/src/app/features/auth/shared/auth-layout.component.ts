import {
  Component,
  Input,
  ViewEncapsulation,
} from '@angular/core';

import {
  AuthIconComponent,
} from './auth-icon.component';


export type AuthLayoutVariant =
  | 'login'
  | 'register'
  | 'verify'
  | 'forgot'
  | 'reset';


@Component({
  selector: 'app-auth-layout',

  standalone: true,

  imports: [
    AuthIconComponent,
  ],

  templateUrl:
    './auth-layout.component.html',

  styleUrls: [
    './auth-layout.component.scss',
    './auth-controls.scss',
    './auth-feedback.scss',
    './auth-variants.scss',
    './auth-responsive.scss',
  ],

  // Los estilos del módulo público de autenticación
  // permanecen limitados bajo .auth-shell.
  // No afectan las pantallas autenticadas del sistema.
  encapsulation:
    ViewEncapsulation.None,
})
export class AuthLayoutComponent {

  @Input()
  variant: AuthLayoutVariant =
    'login';

  readonly year =
    new Date().getFullYear();
}