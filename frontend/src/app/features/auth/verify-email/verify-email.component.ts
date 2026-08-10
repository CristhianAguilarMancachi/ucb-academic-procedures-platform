import {
  Component,
  OnInit,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ActivatedRoute,
  RouterLink,
} from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
  ],
  templateUrl: './verify-email.component.html',
  styleUrl: './verify-email.component.scss',
})
export class VerifyEmailComponent implements OnInit {

  private readonly route = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);

  cargando = true;
  exitoso = false;

  mensaje =
    'Verificando correo...';

  ngOnInit(): void {
    const token =
      this.route.snapshot.queryParamMap.get('token');

    if (!token) {
      this.cargando = false;
      this.mensaje =
        'El enlace de verificación no contiene un token válido.';
      return;
    }

    this.authService.verificarCorreo(token).subscribe({
      next: (respuesta) => {
        this.exitoso = true;
        this.mensaje = respuesta.mensaje;
      },

      error: (error: HttpErrorResponse) => {
        this.mensaje =
          typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'No fue posible verificar el correo.';
      },

      complete: () => {
        this.cargando = false;
      },
    });
  }
}