import {
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';

import { CommonModule } from '@angular/common';

import {
  FormBuilder,
  ReactiveFormsModule,
} from '@angular/forms';

import {
  ActivatedRoute,
  Router,
} from '@angular/router';

import { HttpErrorResponse } from '@angular/common/http';

import {
  AdminUsersService,
} from '../../../../core/admin/admin-users.service';

import {
  EstadoUsuarioAdministracion,
  ListaRolesResponse,
  UsuarioAdministradorDetalleResponse,
} from '../../../../core/admin/admin.models';

import {
  RolResponse,
} from '../../../../core/account/account.models';


@Component({
  selector: 'app-user-detail',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
  ],
  templateUrl: './user-detail.component.html',
  styleUrl: './user-detail.component.scss',
})
export class UserDetailComponent implements OnInit {

  private readonly route =
    inject(ActivatedRoute);

  private readonly router =
    inject(Router);

  private readonly fb =
    inject(FormBuilder);

  private readonly adminUsersService =
    inject(AdminUsersService);


  readonly usuario =
    signal<UsuarioAdministradorDetalleResponse | null>(null);

  readonly rolesDisponibles =
    signal<RolResponse[]>([]);

  readonly cargando =
    signal(true);

  readonly procesando =
    signal(false);

  readonly error =
    signal<string | null>(null);

  readonly mensaje =
    signal<string | null>(null);


  readonly formularioRol =
    this.fb.nonNullable.group({
      id_rol: [0],
    });


  readonly formularioEstado =
    this.fb.nonNullable.group({
      estado: ['activo' as EstadoUsuarioAdministracion],
      motivo: [''],
    });


  ngOnInit(): void {

    const idUsuario =
      Number(
        this.route.snapshot.paramMap.get('id'),
      );

    if (
      !Number.isInteger(idUsuario)
      || idUsuario <= 0
    ) {
      this.error.set(
        'El identificador del usuario no es válido.',
      );

      this.cargando.set(false);

      return;
    }

    this.cargarDatos(idUsuario);
  }


  cargarDatos(
    idUsuario: number,
  ): void {

    this.cargando.set(true);
    this.error.set(null);

    this.adminUsersService
      .obtenerUsuario(idUsuario)
      .subscribe({

        next: (usuario) => {

          this.usuario.set(usuario);

          this.formularioEstado.patchValue({
            estado: usuario.estado,
          });

          this.cargarRolesDisponibles();

          this.cargando.set(false);
        },

        error: (error: HttpErrorResponse) => {

          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No fue posible cargar el usuario.',
          );

          this.cargando.set(false);
        },
      });
  }


  cargarRolesDisponibles(): void {

    this.adminUsersService
      .obtenerRoles()
      .subscribe({

        next: (respuesta: ListaRolesResponse) => {

          this.rolesDisponibles.set(
            respuesta.items,
          );
        },

        error: () => {

          this.error.set(
            'No fue posible cargar el catálogo de roles.',
          );
        },
      });
  }


  tieneRol(
    idRol: number,
  ): boolean {

    return (
      this.usuario()?.roles.some(
        rol => rol.id_rol === idRol,
      )
      ?? false
    );
  }


  asignarRol(): void {

    const usuarioActual =
      this.usuario();

    if (
      !usuarioActual
      || this.procesando()
    ) {
      return;
    }

    const idRol =
      Number(
        this.formularioRol.controls.id_rol.value,
      );

    if (
      !Number.isInteger(idRol)
      || idRol <= 0
    ) {
      this.error.set(
        'Selecciona un rol válido.',
      );

      return;
    }

    if (this.tieneRol(idRol)) {

      this.error.set(
        'El usuario ya tiene asignado ese rol.',
      );

      return;
    }

    this.procesando.set(true);
    this.error.set(null);
    this.mensaje.set(null);

    this.adminUsersService
      .asignarRol(
        usuarioActual.id_usuario,
        {
          id_rol: idRol,
        },
      )
      .subscribe({

        next: () => {

          this.mensaje.set(
            'El rol fue asignado correctamente.',
          );

          this.formularioRol.reset({
            id_rol: 0,
          });

          this.recargarUsuario();
        },

        error: (error: HttpErrorResponse) => {

          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No fue posible asignar el rol.',
          );

          this.procesando.set(false);
        },
      });
  }


  revocarRol(
    rol: RolResponse,
  ): void {

    const usuarioActual =
      this.usuario();

    if (
      !usuarioActual
      || this.procesando()
    ) {
      return;
    }

    this.procesando.set(true);
    this.error.set(null);
    this.mensaje.set(null);

    this.adminUsersService
      .revocarRol(
        usuarioActual.id_usuario,
        rol.id_rol,
        {},
      )
      .subscribe({

        next: () => {

          this.mensaje.set(
            `El rol "${rol.nombre}" fue removido.`,
          );

          this.recargarUsuario();
        },

        error: (error: HttpErrorResponse) => {

          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No fue posible quitar el rol.',
          );

          this.procesando.set(false);
        },
      });
  }


  cambiarEstado(): void {

    const usuarioActual =
      this.usuario();

    if (
      !usuarioActual
      || this.procesando()
    ) {
      return;
    }

    const datos =
      this.formularioEstado.getRawValue();

    this.procesando.set(true);
    this.error.set(null);
    this.mensaje.set(null);

    this.adminUsersService
      .cambiarEstado(
        usuarioActual.id_usuario,
        {
          estado:
            datos.estado as EstadoUsuarioAdministracion,

          motivo:
            datos.motivo.trim() || null,
        },
      )
      .subscribe({

        next: (usuario) => {

          this.usuario.set(usuario);

          this.formularioEstado.patchValue({
            estado: usuario.estado,
            motivo: '',
          });

          this.mensaje.set(
            'El estado del usuario fue actualizado.',
          );

          this.procesando.set(false);
        },

        error: (error: HttpErrorResponse) => {

          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No fue posible cambiar el estado del usuario.',
          );

          this.procesando.set(false);
        },
      });
  }


  recargarUsuario(): void {

    const usuarioActual =
      this.usuario();

    if (!usuarioActual) {
      this.procesando.set(false);
      return;
    }

    this.adminUsersService
      .obtenerUsuario(
        usuarioActual.id_usuario,
      )
      .subscribe({

        next: (usuario) => {

          this.usuario.set(usuario);

          this.procesando.set(false);
        },

        error: () => {

          this.error.set(
            'La operación se realizó, pero no fue posible actualizar la información mostrada.',
          );

          this.procesando.set(false);
        },
      });
  }


  volver(): void {

    this.router.navigate([
      '/admin/usuarios',
    ]);
  }
}