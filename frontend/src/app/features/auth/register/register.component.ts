import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
  ],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss',
})
export class RegisterComponent {

  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);

  cargando = false;
  error: string | null = null;
  mensaje: string | null = null;

  readonly formulario = this.fb.nonNullable.group({
    nombres: [
      '',
      [
        Validators.required,
        Validators.minLength(2),
        Validators.maxLength(100),
      ],
    ],

    apellidos: [
      '',
      [
        Validators.required,
        Validators.minLength(2),
        Validators.maxLength(100),
      ],
    ],

    correo: [
      '',
      [
        Validators.required,
        Validators.email,
      ],
    ],

    contrasena: [
      '',
      [
        Validators.required,
        Validators.minLength(8),
        Validators.maxLength(128),
      ],
    ],

    confirmar_contrasena: [
      '',
      [
        Validators.required,
        Validators.minLength(8),
        Validators.maxLength(128),
      ],
    ],
  });

  registrar(): void {
    if (this.formulario.invalid || this.cargando) {
      this.formulario.markAllAsTouched();
      return;
    }

    const datos = this.formulario.getRawValue();

    if (
      datos.contrasena !==
      datos.confirmar_contrasena
    ) {
      this.error = 'Las contraseñas no coinciden.';
      return;
    }

    this.cargando = true;
    this.error = null;
    this.mensaje = null;

    this.authService.registrar(datos).subscribe({
      next: (respuesta) => {
        this.mensaje = respuesta.mensaje;
        this.formulario.reset();
      },

      error: (error: HttpErrorResponse) => {
        this.error =
          typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'No fue posible crear la cuenta.';

        this.cargando = false;
      },

      complete: () => {
        this.cargando = false;
      },
    });
  }
}