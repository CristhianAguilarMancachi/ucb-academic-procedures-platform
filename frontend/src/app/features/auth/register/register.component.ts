import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  DestroyRef,
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
  FormControl,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

import {
  Router,
  RouterLink,
} from '@angular/router';

import {
  HttpErrorResponse,
} from '@angular/common/http';

import {
  timer,
} from 'rxjs';

import {
  takeUntilDestroyed,
} from '@angular/core/rxjs-interop';

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
  selector:
    'app-register',

  standalone:
    true,

  imports: [
    AuthLayoutComponent,
    AuthIconComponent,
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
  ],

  templateUrl:
    './register.component.html',

  styleUrl:
    './register.component.scss',
})
export class RegisterComponent
  implements AfterViewInit {

  private readonly fb =
    inject(FormBuilder);

  private readonly authService =
    inject(AuthService);

  private readonly googleIdentityService =
    inject(GoogleIdentityService);

  private readonly changeDetector =
    inject(ChangeDetectorRef);

  private readonly destroyRef =
    inject(DestroyRef);

  private readonly router =
    inject(Router);

  private readonly ngZone =
    inject(NgZone);


  @ViewChild('googleButton')
  private googleButton?:
    ElementRef<HTMLDivElement>;


  registrado =
    false;

  mostrarContrasena =
    false;

  mostrarConfirmacion =
    false;

  cargando =
    false;

  cargandoGoogle =
    false;

  googleDisponible =
    true;

  error:
    string
    | null =
    null;

  mensaje:
    string
    | null =
    null;


  readonly correoReenvio =
    new FormControl(
      '',
      {
        nonNullable:
          true,

        validators: [
          Validators.required,
          Validators.email,
        ],
      },
    );


  reenviando =
    false;

  esperandoReenvio =
    false;

  mensajeReenvio:
    string
    | null =
    null;

  errorReenvio:
    string
    | null =
    null;


  readonly formulario =
    this.fb.nonNullable.group({

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


  ngAfterViewInit():
    void {

    void this.inicializarGoogle();
  }


  // =========================================================
  // GOOGLE
  // =========================================================

  private async inicializarGoogle():
    Promise<void> {

    if (
      !this.googleButton
    ) {
      return;
    }


    try {

      await this.googleIdentityService
        .renderizarBoton(
          this.googleButton.nativeElement,

          (
            credential:
              string,
          ) => {

            this.ngZone.run(
              () => {

                this.registrarConGoogle(
                  credential,
                );
              },
            );
          },

          'register',
        );

    } catch {

      this.googleDisponible =
        false;

      this.changeDetector
        .detectChanges();
    }
  }


  private registrarConGoogle(
    credential:
      string,
  ): void {

    if (
      this.cargandoGoogle
      || this.cargando
    ) {
      return;
    }


    this.cargandoGoogle =
      true;

    this.error =
      null;


    this.authService
      .loginGoogle(
        credential,
      )
      .pipe(
        takeUntilDestroyed(
          this.destroyRef,
        ),
      )
      .subscribe({

        next:
          () => {

            void this.router
              .navigateByUrl(
                '/informacion',
              );
          },


        error:
          (
            error:
              HttpErrorResponse,
          ) => {

            this.error =
              typeof error.error?.detail
              === 'string'

                ? error.error.detail

                : 'No fue posible continuar con Google.';

            this.cargandoGoogle =
              false;

            this.changeDetector
              .markForCheck();
          },


        complete:
          () => {

            this.cargandoGoogle =
              false;

            this.changeDetector
              .markForCheck();
          },
      });
  }


  // =========================================================
  // REENVÍO DE VERIFICACIÓN
  // =========================================================

  reenviar():
    void {

    if (
      this.correoReenvio.invalid
      || this.reenviando
      || this.esperandoReenvio
    ) {

      this.correoReenvio
        .markAsTouched();

      return;
    }


    this.reenviando =
      true;

    this.mensajeReenvio =
      null;

    this.errorReenvio =
      null;


    this.authService
      .reenviarVerificacion(
        this.correoReenvio
          .value
          .trim(),
      )
      .pipe(
        takeUntilDestroyed(
          this.destroyRef,
        ),
      )
      .subscribe({

        next:
          (
            respuesta,
          ) => {

            this.reenviando =
              false;

            this.changeDetector
              .markForCheck();

            this.mensajeReenvio =
              respuesta.mensaje;

            this.esperandoReenvio =
              true;


            timer(
              60_000,
            )
              .pipe(
                takeUntilDestroyed(
                  this.destroyRef,
                ),
              )
              .subscribe(
                () => {

                  this.esperandoReenvio =
                    false;

                  this.changeDetector
                    .markForCheck();
                },
              );
          },


        error:
          () => {

            this.reenviando =
              false;

            this.changeDetector
              .markForCheck();

            this.errorReenvio =
              'No fue posible procesar la solicitud. Inténtalo de nuevo más tarde.';
          },
      });
  }


  // =========================================================
  // REGISTRO TRADICIONAL
  // =========================================================

  registrar():
    void {

    if (
      this.formulario.invalid
      || this.cargando
      || this.cargandoGoogle
    ) {

      this.formulario
        .markAllAsTouched();

      return;
    }


    const datos =
      this.formulario
        .getRawValue();


    if (
      datos.contrasena
      !== datos.confirmar_contrasena
    ) {

      this.error =
        'Las contraseñas no coinciden.';

      return;
    }


    this.cargando =
      true;

    this.error =
      null;

    this.mensaje =
      null;


    this.authService
      .registrar(
        datos,
      )
      .pipe(
        takeUntilDestroyed(
          this.destroyRef,
        ),
      )
      .subscribe({

        next:
          (
            respuesta,
          ) => {

            this.mensaje =
              respuesta.mensaje;

            this.correoReenvio
              .setValue(
                datos.correo,
              );

            this.registrado =
              true;

            this.formulario
              .reset();
          },


        error:
          (
            error:
              HttpErrorResponse,
          ) => {

            this.error =
              typeof error.error?.detail
              === 'string'

                ? error.error.detail

                : 'No fue posible crear la cuenta.';

            this.cargando =
              false;

            this.changeDetector
              .markForCheck();
          },


        complete:
          () => {

            this.cargando =
              false;

            this.changeDetector
              .markForCheck();
          },
      });
  }
}