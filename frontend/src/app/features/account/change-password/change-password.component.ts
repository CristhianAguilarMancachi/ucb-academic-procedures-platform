import {
  Component,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-change-password',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
  ],
  templateUrl: './change-password.component.html',
  styleUrl: './change-password.component.scss',
})
export class ChangePasswordComponent {

  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly guardando = signal(false);

  readonly error = signal<string | null>(null);
  readonly mensaje = signal<string | null>(null);

  readonly formulario = this.fb.nonNullable.group({
    contrasena_actual: [
      '',
      [
        Validators.required,
      ],
    ],

    nueva_contrasena: [
      '',
      [
        Validators.required,
        Validators.minLength(8),
      ],
    ],

    confirmar_nueva_contrasena: [
      '',
      [
        Validators.required,
        Validators.minLength(8),
      ],
    ],
  });

  cambiarContrasena(): void {
    if (
      this.formulario.invalid
      || this.guardando()
    ) {
      this.formulario.markAllAsTouched();
      return;
    }

    const datos = this.formulario.getRawValue();

    if (
      datos.nueva_contrasena
      !== datos.confirmar_nueva_contrasena
    ) {
      this.error.set(
        'La nueva contraseña y su confirmación no coinciden.',
      );

      return;
    }

    if (
      datos.contrasena_actual
      === datos.nueva_contrasena
    ) {
      this.error.set(
        'La nueva contraseña debe ser diferente de la actual.',
      );

      return;
    }

    this.guardando.set(true);
    this.error.set(null);
    this.mensaje.set(null);

    this.authService.cambiarContrasena({
      contrasena_actual:
        datos.contrasena_actual,

      nueva_contrasena:
        datos.nueva_contrasena,

      confirmar_nueva_contrasena:
        datos.confirmar_nueva_contrasena,
    }).subscribe({
      next: () => {
        this.mensaje.set(
          'La contraseña fue actualizada correctamente. Debes iniciar sesión nuevamente.',
        );

        this.guardando.set(false);

        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 1500);
      },

      error: (error: HttpErrorResponse) => {
        this.error.set(
          typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'No fue posible cambiar la contraseña.',
        );

        this.guardando.set(false);
      },
    });
  }
}