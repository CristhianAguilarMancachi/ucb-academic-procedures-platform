import {
  Component,
  OnInit,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import {
  ActivatedRoute,
  RouterLink,
} from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
  ],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.scss',
})
export class ResetPasswordComponent implements OnInit {

  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);

  token: string | null = null;

  cargando = false;
  error: string | null = null;
  mensaje: string | null = null;

  readonly formulario = this.fb.nonNullable.group({
    nueva_contrasena: [
      '',
      [
        Validators.required,
        Validators.minLength(8),
        Validators.maxLength(128),
      ],
    ],

    confirmar_nueva_contrasena: [
      '',
      [
        Validators.required,
        Validators.minLength(8),
        Validators.maxLength(128),
      ],
    ],
  });

  ngOnInit(): void {
    this.token =
      this.route.snapshot.queryParamMap.get('token');

    if (!this.token) {
      this.error =
        'El enlace de recuperación no contiene un token válido.';
    }
  }

  restablecer(): void {
    if (
      this.formulario.invalid
      || this.cargando
      || !this.token
    ) {
      this.formulario.markAllAsTouched();
      return;
    }

    const datosFormulario =
      this.formulario.getRawValue();

    if (
      datosFormulario.nueva_contrasena !==
      datosFormulario.confirmar_nueva_contrasena
    ) {
      this.error =
        'Las contraseñas no coinciden.';
      return;
    }

    this.cargando = true;
    this.error = null;

    this.authService.restablecerContrasena({
      token: this.token,
      nueva_contrasena:
        datosFormulario.nueva_contrasena,
      confirmar_nueva_contrasena:
        datosFormulario.confirmar_nueva_contrasena,
    }).subscribe({
      next: (respuesta) => {
        this.mensaje = respuesta.mensaje;
        this.formulario.disable();
      },

      error: (error: HttpErrorResponse) => {
        this.error =
          typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'No fue posible restablecer la contraseña.';

        this.cargando = false;
      },

      complete: () => {
        this.cargando = false;
      },
    });
  }
}