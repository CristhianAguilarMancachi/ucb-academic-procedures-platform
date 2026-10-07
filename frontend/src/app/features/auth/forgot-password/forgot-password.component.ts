import { ChangeDetectorRef, Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthLayoutComponent } from '../shared/auth-layout.component';
import { AuthIconComponent } from '../shared/auth-icon.component';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [AuthLayoutComponent, AuthIconComponent, CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss',
})
export class ForgotPasswordComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly changeDetector = inject(ChangeDetectorRef);

  cargando = false;
  mensaje: string | null = null;

  readonly formulario = this.fb.nonNullable.group({
    correo: ['', [Validators.required, Validators.email]],
  });

  solicitar(): void {
    if (this.formulario.invalid || this.cargando) {
      this.formulario.markAllAsTouched();
      return;
    }

    this.cargando = true;
    this.mensaje = null;

    const correo = this.formulario.controls.correo.value;

    this.authService.solicitarRecuperacion(correo).subscribe({
      next: (respuesta) => {
        this.mensaje = respuesta.mensaje;
      },

      error: () => {
        this.cargando = false;
        this.changeDetector.markForCheck();
        /*
         * No mostramos información que permita saber
         * si un correo existe o no.
         */
        this.mensaje =
          'Si el correo está asociado a una cuenta válida, ' +
          'recibirás instrucciones para restablecer ' +
          'la contraseña.';
      },

      complete: () => {
        this.cargando = false;
        this.changeDetector.markForCheck();
      },
    });
  }
}
