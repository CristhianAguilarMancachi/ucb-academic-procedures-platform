import {
  Component,
  OnInit,
  computed,
  inject,
  signal,
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
  HttpErrorResponse,
} from '@angular/common/http';

import {
  Router,
} from '@angular/router';

import {
  NgIcon,
  provideIcons,
} from '@ng-icons/core';

import {
  heroEye,
  heroEyeSlash,
  heroInformationCircle,
  heroLockClosed,
} from '@ng-icons/heroicons/outline';

import {
  AuthService,
} from '../../../core/auth/auth.service';

import {
  AccountService,
} from '../../../core/account/account.service';

import {
  UsuarioAutenticadoResponse,
} from '../../../core/account/account.models';


@Component({
  selector:
    'app-change-password',

  standalone:
    true,

  imports: [
    CommonModule,
    ReactiveFormsModule,
    NgIcon,
  ],

  providers: [
    provideIcons({
      heroEye,
      heroEyeSlash,
      heroInformationCircle,
      heroLockClosed,
    }),
  ],

  templateUrl:
    './change-password.component.html',

  styleUrl:
    './change-password.component.scss',
})
export class ChangePasswordComponent
  implements OnInit {

  private readonly fb =
    inject(FormBuilder);

  private readonly authService =
    inject(AuthService);

  private readonly accountService =
    inject(AccountService);

  private readonly router =
    inject(Router);


  readonly usuario =
    signal<UsuarioAutenticadoResponse | null>(
      null,
    );


  readonly cargandoCuenta =
    signal(true);

  readonly guardando =
    signal(false);

  readonly error =
    signal<string | null>(
      null,
    );

  readonly mensaje =
    signal<string | null>(
      null,
    );


  readonly tieneContrasena =
    computed(
      () =>
        this.usuario()
          ?.tiene_contrasena
        ?? false,
    );


  readonly correo =
    computed(
      () => {

        const correos =
          this.usuario()
            ?.correos
          ?? [];

        /*
         * Priorizamos el correo activo y principal.
         * Si por datos históricos no existiera, usamos
         * cualquier correo activo.
         */
        return (
          correos.find(
            (item) =>
              item.activo
              && item.es_principal,
          )
          ?? correos.find(
            (item) =>
              item.activo,
          )
        )?.correo
        ?? '';
      },
    );


  mostrarContrasenaActual =
    false;

  mostrarNuevaContrasena =
    false;

  mostrarConfirmacion =
    false;


  readonly formulario =
    this.fb.nonNullable.group({

      contrasena_actual: [
        '',
        [
          Validators.required,
          Validators.maxLength(
            128,
          ),
        ],
      ],

      nueva_contrasena: [
        '',
        [
          Validators.required,
          Validators.minLength(
            8,
          ),
          Validators.maxLength(
            128,
          ),
        ],
      ],

      confirmar_nueva_contrasena: [
        '',
        [
          Validators.required,
          Validators.minLength(
            8,
          ),
          Validators.maxLength(
            128,
          ),
        ],
      ],
    });


  ngOnInit(): void {

    /*
     * Consultamos /users/me en lugar de depender únicamente
     * del estado en memoria de AuthService.
     *
     * Esto permite que la pantalla funcione correctamente
     * incluso si el usuario recarga directamente esta URL.
     */
    this.accountService
      .obtenerPerfil()
      .subscribe({

        next:
          (
            usuario,
          ) => {

            this.usuario.set(
              usuario,
            );

            this.cargandoCuenta.set(
              false,
            );
          },


        error:
          (
            error:
              HttpErrorResponse,
          ) => {

            this.error.set(
              typeof error
                .error
                ?.detail
                === 'string'

                ? error
                    .error
                    .detail

                : 'No fue posible obtener la información de seguridad de la cuenta.',
            );

            this.cargandoCuenta.set(
              false,
            );
          },
      });
  }


  // =========================================================
  // CAMBIAR CONTRASEÑA EXISTENTE
  // =========================================================


  cambiarContrasena():
    void {

    /*
     * Este flujo solo corresponde a cuentas que ya tienen
     * una contraseña local configurada.
     */
    if (
      !this.tieneContrasena()
    ) {
      return;
    }


    if (
      this.formulario.invalid
      || this.guardando()
    ) {

      this.formulario
        .markAllAsTouched();

      return;
    }


    const datos =
      this.formulario
        .getRawValue();


    if (
      datos.nueva_contrasena
      !==
      datos
        .confirmar_nueva_contrasena
    ) {

      this.error.set(
        'La nueva contraseña y su confirmación no coinciden.',
      );

      return;
    }


    if (
      datos.contrasena_actual
      ===
      datos.nueva_contrasena
    ) {

      this.error.set(
        'La nueva contraseña debe ser diferente de la actual.',
      );

      return;
    }


    this.guardando.set(
      true,
    );

    this.error.set(
      null,
    );

    this.mensaje.set(
      null,
    );


    this.authService
      .cambiarContrasena({

        contrasena_actual:
          datos
            .contrasena_actual,

        nueva_contrasena:
          datos
            .nueva_contrasena,

        confirmar_nueva_contrasena:
          datos
            .confirmar_nueva_contrasena,

      })
      .subscribe({

        next: () => {

          this.mensaje.set(
            'La contraseña fue actualizada correctamente. Debes iniciar sesión nuevamente.',
          );

          this.guardando.set(
            false,
          );


          setTimeout(
            () => {

              this.router.navigate(
                [
                  '/login',
                ],
                {
                  replaceUrl:
                    true,
                },
              );

            },
            1500,
          );
        },


        error:
          (
            error:
              HttpErrorResponse,
          ) => {

            this.error.set(
              typeof error
                .error
                ?.detail
                === 'string'

                ? error
                    .error
                    .detail

                : 'No fue posible cambiar la contraseña.',
            );

            this.guardando.set(
              false,
            );
          },
      });
  }


  // =========================================================
  // ESTABLECER PRIMERA CONTRASEÑA
  // =========================================================


  establecerContrasena():
    void {

    /*
     * Una cuenta que ya tiene contraseña debe utilizar
     * exclusivamente el flujo normal de cambio.
     */
    if (
      this.tieneContrasena()
      || this.guardando()
    ) {
      return;
    }


    const correo =
      this.correo();


    if (
      !correo
    ) {

      this.error.set(
        'No se encontró un correo activo asociado a la cuenta.',
      );

      return;
    }


    this.guardando.set(
      true,
    );

    this.error.set(
      null,
    );

    this.mensaje.set(
      null,
    );


    /*
     * Reutilizamos el flujo seguro existente de recuperación.
     *
     * El usuario recibirá un token temporal por correo y
     * utilizará la misma pantalla de restablecimiento que una
     * recuperación convencional.
     */
    this.authService
      .solicitarRecuperacion(
        correo,
      )
      .subscribe({

        next: () => {

          this.mensaje.set(
            'La solicitud fue procesada. Revisa tu correo para establecer una contraseña para esta cuenta.',
          );

          this.guardando.set(
            false,
          );
        },


        error:
          (
            error:
              HttpErrorResponse,
          ) => {

            this.error.set(
              typeof error
                .error
                ?.detail
                === 'string'

                ? error
                    .error
                    .detail

                : 'No fue posible solicitar el enlace para establecer la contraseña.',
            );

            this.guardando.set(
              false,
            );
          },
      });
  }


  // =========================================================
  // CANCELAR
  // =========================================================


  cancelar():
    void {

    if (
      this.guardando()
    ) {
      return;
    }


    this.router.navigate([
      '/perfil',
    ]);
  }
}