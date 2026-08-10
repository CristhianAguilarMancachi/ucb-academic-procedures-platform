import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import {
  ActivatedRoute,
  Router,
  RouterLink,
} from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {

  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  cargando = false;
  error: string | null = null;

  readonly formulario = this.fb.nonNullable.group({
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
      ],
    ],
  });

  iniciarSesion(): void {
    if (this.formulario.invalid || this.cargando) {
      this.formulario.markAllAsTouched();
      return;
    }

    this.cargando = true;
    this.error = null;

    this.authService.login(
      this.formulario.getRawValue(),
    ).subscribe({
      next: () => {
        const returnUrl =
          this.route.snapshot.queryParamMap.get(
            'returnUrl',
          ) ?? '/informacion';

        this.router.navigateByUrl(returnUrl);
      },

      error: (error: HttpErrorResponse) => {
        this.error = this.obtenerMensajeError(error);
        this.cargando = false;
      },

      complete: () => {
        this.cargando = false;
      },
    });
  }

  private obtenerMensajeError(
    error: HttpErrorResponse,
  ): string {
    if (
      typeof error.error?.detail === 'string'
    ) {
      return error.error.detail;
    }

    return 'No fue posible iniciar sesión.';
  }
}