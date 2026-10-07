import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  NgZone,
  ViewChild,
  inject,
} from '@angular/core';

import {
  CommonModule,
} from '@angular/common';

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

import {
  HttpErrorResponse,
} from '@angular/common/http';

import {
  AuthLayoutComponent,
} from '../shared/auth-layout.component';

import {
  AuthIconComponent,
} from '../shared/auth-icon.component';

import {
  AuthService,
} from '../../../core/auth/auth.service';

import {
  GoogleIdentityService,
} from '../../../core/auth/google-identity.service';


@Component({
  selector: 'app-login',
  standalone: true,

  imports: [
    AuthLayoutComponent,
    AuthIconComponent,
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
  ],

  templateUrl:
    './login.component.html',

  styleUrl:
    './login.component.scss',
})
export class LoginComponent
  implements AfterViewInit {

  private readonly fb =
    inject(FormBuilder);

  private readonly authService =
    inject(AuthService);

  private readonly googleIdentityService =
    inject(GoogleIdentityService);

  private readonly changeDetector =
    inject(ChangeDetectorRef);

  private readonly router =
    inject(Router);

  private readonly route =
    inject(ActivatedRoute);

  private readonly ngZone =
    inject(NgZone);


  @ViewChild(
    'googleButton',
  )
  private googleButton?:
    ElementRef<HTMLDivElement>;


  mostrarContrasena = false;

  cargando = false;

  cargandoGoogle = false;

  googleDisponible = true;

  error: string | null = null;


  readonly formulario =
    this.fb.nonNullable.group({

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


  // =========================================================
  // INICIALIZACIÓN GOOGLE
  // =========================================================

  ngAfterViewInit(): void {
    void this.inicializarGoogle();
  }


  private async inicializarGoogle():
    Promise<void> {

    if (!this.googleButton) {
      return;
    }

    try {

      await this.googleIdentityService
        .renderizarBoton(

          this.googleButton
            .nativeElement,

          (
            credential: string,
          ) => {

            this.ngZone.run(
              () => {
                this.iniciarSesionGoogle(
                  credential,
                );
              },
            );

          },

          'login',
        );

    } catch {

      this.googleDisponible =
        false;

      this.changeDetector
        .detectChanges();
    }
  }


  // =========================================================
  // LOGIN GOOGLE
  // =========================================================

  private iniciarSesionGoogle(
    credential: string,
  ): void {

    if (
      this.cargandoGoogle
      || this.cargando
    ) {
      return;
    }

    this.cargandoGoogle = true;
    this.error = null;


    this.authService
      .loginGoogle(
        credential,
      )
      .subscribe({

        next: () => {
          this.irDespuesDeLogin();
        },

        error: (
          error:
            HttpErrorResponse,
        ) => {

          this.error =
            this.obtenerMensajeError(
              error,
            );

          this.cargandoGoogle =
            false;

          this.changeDetector
            .markForCheck();
        },

        complete: () => {

          this.cargandoGoogle =
            false;

          this.changeDetector
            .markForCheck();
        },

      });
  }


  // =========================================================
  // LOGIN TRADICIONAL
  // =========================================================

  iniciarSesion(): void {

    if (
      this.formulario.invalid
      || this.cargando
      || this.cargandoGoogle
    ) {

      this.formulario
        .markAllAsTouched();

      return;
    }

    this.cargando = true;
    this.error = null;


    this.authService
      .login(
        this.formulario
          .getRawValue(),
      )
      .subscribe({

        next: () => {
          this.irDespuesDeLogin();
        },

        error: (
          error:
            HttpErrorResponse,
        ) => {

          this.error =
            this.obtenerMensajeError(
              error,
            );

          this.cargando = false;

          this.changeDetector
            .markForCheck();
        },

        complete: () => {

          this.cargando = false;

          this.changeDetector
            .markForCheck();
        },

      });
  }


  // =========================================================
  // REDIRECCIÓN
  // =========================================================

  private irDespuesDeLogin():
    void {

    const returnUrl =
      this.route
        .snapshot
        .queryParamMap
        .get(
          'returnUrl',
        )
      ?? '/informacion';

    void this.router
      .navigateByUrl(
        returnUrl,
      );
  }


  // =========================================================
  // ERRORES
  // =========================================================

  private obtenerMensajeError(
    error: HttpErrorResponse,
  ): string {

    if (
      typeof error.error?.detail
      === 'string'
    ) {
      return error.error.detail;
    }

    return (
      'No fue posible iniciar sesión.'
    );
  }
}