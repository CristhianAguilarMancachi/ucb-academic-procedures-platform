import { ChangeDetectorRef, Component, DestroyRef, OnInit, inject } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { timer } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AuthLayoutComponent } from '../shared/auth-layout.component';
import { AuthIconComponent } from '../shared/auth-icon.component';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [AuthLayoutComponent, AuthIconComponent, CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './verify-email.component.html',
  styleUrl: './verify-email.component.scss',
})
export class VerifyEmailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly location = inject(Location);
  private readonly authService = inject(AuthService);
  private readonly changeDetector = inject(ChangeDetectorRef);

  private readonly destroyRef = inject(DestroyRef);
  readonly correoReenvio = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.email],
  });
  reenviando = false;
  esperandoReenvio = false;
  mensajeReenvio: string | null = null;
  errorReenvio: string | null = null;

  reenviar(): void {
    if (this.correoReenvio.invalid || this.reenviando || this.esperandoReenvio) {
      this.correoReenvio.markAsTouched();
      return;
    }
    this.reenviando = true;
    this.mensajeReenvio = null;
    this.errorReenvio = null;
    this.authService
      .reenviarVerificacion(this.correoReenvio.value.trim())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (respuesta) => {
          this.reenviando = false;
          this.changeDetector.markForCheck();
          this.mensajeReenvio = respuesta.mensaje;
          this.esperandoReenvio = true;
          timer(60_000)
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(() => {
              this.esperandoReenvio = false;
              this.changeDetector.markForCheck();
            });
        },
        error: () => {
          this.reenviando = false;
          this.changeDetector.markForCheck();
          this.errorReenvio = 'No fue posible procesar la solicitud. Inténtalo de nuevo más tarde.';
        },
      });
  }

  cargando = true;
  exitoso = false;

  mensaje = 'Verificando correo...';

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');

    if (token !== null) {
      const url = this.router.parseUrl(this.router.url);
      delete url.queryParams['token'];
      this.location.replaceState(this.router.serializeUrl(url));
    }

    if (!token) {
      this.cargando = false;
      this.changeDetector.markForCheck();
      this.mensaje = 'El enlace de verificación no contiene un token válido.';
      return;
    }

    this.authService.verificarCorreo(token).subscribe({
      next: (respuesta) => {
        this.exitoso = true;
        this.mensaje = respuesta.mensaje;
      },

      error: (error: HttpErrorResponse) => {
        this.cargando = false;
        this.changeDetector.markForCheck();
        this.mensaje =
          typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'No fue posible verificar el correo.';
      },

      complete: () => {
        this.cargando = false;
        this.changeDetector.markForCheck();
      },
    });
  }
}
