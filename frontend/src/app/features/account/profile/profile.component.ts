import {
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';

import {
  CommonModule,
} from '@angular/common';

import {
  HttpClient,
  HttpErrorResponse,
} from '@angular/common/http';

import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

import {
  RouterLink,
} from '@angular/router';

import {
  catchError,
  forkJoin,
  of,
} from 'rxjs';

import {
  NgIcon,
  provideIcons,
} from '@ng-icons/core';

import {
  heroCalendarDays,
  heroCheck,
  heroCheckCircle,
  heroClock,
  heroEnvelope,
  heroIdentification,
  heroLockClosed,
  heroPencilSquare,
  heroPhone,
  heroShieldCheck,
  heroUser,
  heroXMark,
} from '@ng-icons/heroicons/outline';

import {
  AccountService,
} from '../../../core/account/account.service';

import {
  UsuarioAutenticadoResponse,
} from '../../../core/account/account.models';


interface PerfilAcademicoResponse {
  id_perfil?: number;
  id_usuario?: number;

  documento_identidad:
    | string
    | null;

  carrera_programa?:
    string
    | null;

  codigo_estudiante?:
    string
    | null;

  sede?:
    string
    | null;

  nivel_academico?:
    string
    | null;

  fecha_creacion?:
    string;

  fecha_actualizacion?:
    string;
}


@Component({
  selector: 'app-profile',

  standalone: true,

  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    NgIcon,
  ],

  providers: [
    provideIcons({
      heroCalendarDays,
      heroCheck,
      heroCheckCircle,
      heroClock,
      heroEnvelope,
      heroIdentification,
      heroLockClosed,
      heroPencilSquare,
      heroPhone,
      heroShieldCheck,
      heroUser,
      heroXMark,
    }),
  ],

  templateUrl:
    './profile.component.html',

  styleUrl:
    './profile.component.scss',
})
export class ProfileComponent
  implements OnInit {

  private readonly fb =
    inject(FormBuilder);

  private readonly http =
    inject(HttpClient);

  private readonly accountService =
    inject(AccountService);


  readonly usuario =
    signal<
      UsuarioAutenticadoResponse
      | null
    >(
      null,
    );


  readonly perfilAcademico =
    signal<PerfilAcademicoResponse>({
      documento_identidad:
        null,
    });


  readonly cargando =
    signal(true);

  readonly guardando =
    signal(false);

  readonly editando =
    signal(false);


  readonly error =
    signal<string | null>(
      null,
    );

  readonly mensaje =
    signal<string | null>(
      null,
    );


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

      documento_identidad: [
        '',
        [
          Validators.required,
          Validators.minLength(3),
          Validators.maxLength(50),
        ],
      ],

      telefono: [
        '',
        [
          Validators.minLength(7),
          Validators.maxLength(30),
        ],
      ],
    });


  ngOnInit(): void {
    this.cargarPerfil();
  }


  // =========================================================
  // CARGA
  // =========================================================

  cargarPerfil(): void {

    this.cargando.set(
      true,
    );

    this.error.set(
      null,
    );


    forkJoin({

      usuario:
        this.accountService
          .obtenerPerfil(),

      academico:
        this.http
          .get<PerfilAcademicoResponse>(
            '/api/users/me/perfil-academico',
          )
          .pipe(
            catchError(
              (
                error:
                  HttpErrorResponse,
              ) => {

                if (
                  error.status
                  === 404
                ) {
                  return of<PerfilAcademicoResponse>({
                    documento_identidad:
                      null,
                  });
                }

                throw error;
              },
            ),
          ),

    }).subscribe({

      next:
        ({
          usuario,
          academico,
        }) => {

          this.usuario.set(
            usuario,
          );

          this.perfilAcademico.set(
            academico,
          );

          this.actualizarFormulario();

          this.cargando.set(
            false,
          );
        },


      error:
        () => {

          this.error.set(
            'No fue posible cargar la información del perfil.',
          );

          this.cargando.set(
            false,
          );
        },
    });
  }


  // =========================================================
  // EDICIÓN
  // =========================================================

  iniciarEdicion(): void {

    this.actualizarFormulario();

    this.error.set(
      null,
    );

    this.mensaje.set(
      null,
    );

    this.editando.set(
      true,
    );
  }


  cancelarEdicion(): void {

    if (
      this.guardando()
    ) {
      return;
    }


    this.actualizarFormulario();

    this.formulario
      .markAsPristine();

    this.formulario
      .markAsUntouched();


    this.error.set(
      null,
    );

    this.mensaje.set(
      null,
    );

    this.editando.set(
      false,
    );
  }


  guardarCambios(): void {

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


    const telefono =
      datos.telefono
        .trim();


    this.guardando.set(
      true,
    );

    this.error.set(
      null,
    );

    this.mensaje.set(
      null,
    );


    forkJoin({

      usuario:
        this.accountService
          .actualizarPerfil({

            nombres:
              datos.nombres.trim(),

            apellidos:
              datos.apellidos.trim(),

            telefono:
              telefono
                ? telefono
                : null,
          }),

      academico:
        this.http
          .patch<PerfilAcademicoResponse>(
            '/api/users/me/perfil-academico',
            {
              documento_identidad:
                datos
                  .documento_identidad
                  .trim(),
            },
          ),

    }).subscribe({

      next:
        ({
          usuario,
          academico,
        }) => {

          this.usuario.set(
            usuario,
          );

          this.perfilAcademico.set(
            academico,
          );

          this.actualizarFormulario();

          this.formulario
            .markAsPristine();

          this.formulario
            .markAsUntouched();

          this.editando.set(
            false,
          );

          this.guardando.set(
            false,
          );

          this.mensaje.set(
            'Los datos del perfil fueron actualizados correctamente.',
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

              : 'No fue posible actualizar el perfil.',
          );

          this.guardando.set(
            false,
          );
        },
    });
  }


  private actualizarFormulario():
    void {

    const usuario =
      this.usuario();

    if (
      !usuario
    ) {
      return;
    }


    this.formulario.setValue({

      nombres:
        usuario.nombres,

      apellidos:
        usuario.apellidos,

      documento_identidad:
        this.perfilAcademico()
          .documento_identidad
        || '',

      telefono:
        usuario.telefono
        || '',
    });
  }


  // =========================================================
  // CORREO
  // =========================================================

  obtenerCorreo(): string {

    return (
      this.usuario()
        ?.correos
        .find(
          (
            correo,
          ) =>
            correo.activo,
        )
        ?.correo
      ?? 'Sin correo registrado'
    );
  }


  correoVerificado():
    boolean {

    return (
      this.usuario()
        ?.correos
        .find(
          (
            correo,
          ) =>
            correo.activo,
        )
        ?.verificado
      ?? false
    );
  }


  // =========================================================
  // PRESENTACIÓN
  // =========================================================

  nombreCompleto(): string {

    const usuario =
      this.usuario();


    if (
      !usuario
    ) {
      return '';
    }


    return (
      `${usuario.nombres} ${usuario.apellidos}`
    );
  }


  rolPrincipal(): string {

    const roles =
      this.usuario()
        ?.roles
        .map(
          (
            rol,
          ) =>
            rol.nombre,
        )
      ?? [];


    if (
      roles.includes(
        'administrador',
      )
    ) {
      return 'Administrador';
    }


    if (
      roles.includes(
        'personal_administrativo',
      )
    ) {
      return 'Personal administrativo';
    }


    return 'Estudiante';
  }


  etiquetaEstado(): string {

    const estado =
      this.usuario()
        ?.estado;


    const etiquetas:
      Record<
        string,
        string
      > = {

      activo:
        'Activo',

      pendiente_verificacion:
        'Pendiente de verificación',

      bloqueado:
        'Bloqueado',

      inactivo:
        'Inactivo',
    };


    return (
      estado
        ? etiquetas[estado]
          || estado
        : 'Sin información'
    );
  }


  formatearFecha(
    fecha:
      string
      | Date
      | null
      | undefined,
  ): string {

    if (
      !fecha
    ) {
      return 'Sin información';
    }


    const valor =
      new Date(
        fecha,
      );


    if (
      Number.isNaN(
        valor.getTime(),
      )
    ) {
      return 'Sin información';
    }


    return (
      new Intl.DateTimeFormat(
        'es-BO',
        {
          day:
            '2-digit',

          month:
            '2-digit',

          year:
            'numeric',
        },
      )
        .format(
          valor,
        )
    );
  }


  formatearFechaHora(
    fecha:
      string
      | Date
      | null
      | undefined,
  ): string {

    if (
      !fecha
    ) {
      return 'Sin información';
    }


    const valor =
      new Date(
        fecha,
      );


    if (
      Number.isNaN(
        valor.getTime(),
      )
    ) {
      return 'Sin información';
    }


    return (
      new Intl.DateTimeFormat(
        'es-BO',
        {
          day:
            '2-digit',

          month:
            '2-digit',

          year:
            'numeric',

          hour:
            '2-digit',

          minute:
            '2-digit',
        },
      )
        .format(
          valor,
        )
    );
  }
}