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
  Router,
} from '@angular/router';

import { HttpErrorResponse } from '@angular/common/http';

import {
  AdminUsersService,
} from '../../../../core/admin/admin-users.service';

import {
  EstadoUsuarioAdministracion,
  UsuarioResumenResponse,
} from '../../../../core/admin/admin.models';


@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
  ],
  templateUrl: './user-list.component.html',
  styleUrl: './user-list.component.scss',
})
export class UserListComponent implements OnInit {

  private readonly fb = inject(FormBuilder);

  private readonly adminUsersService =
    inject(AdminUsersService);

  private readonly router = inject(Router);


  readonly usuarios =
    signal<UsuarioResumenResponse[]>([]);

  readonly cargando =
    signal(true);

  readonly error =
    signal<string | null>(null);


  readonly total =
    signal(0);

  readonly pagina =
    signal(1);

  readonly porPagina =
    signal(20);


  readonly formulario = this.fb.nonNullable.group({
    busqueda: [''],
    estado: [''],
  });


  ngOnInit(): void {
    this.cargarUsuarios();
  }


  cargarUsuarios(): void {

    this.cargando.set(true);
    this.error.set(null);

    const filtros =
      this.formulario.getRawValue();

    const estado =
      filtros.estado
        ? filtros.estado as EstadoUsuarioAdministracion
        : undefined;

    this.adminUsersService.listarUsuarios({
      pagina: this.pagina(),
      por_pagina: this.porPagina(),
      estado,
      busqueda:
        filtros.busqueda.trim() || undefined,
    }).subscribe({

      next: (respuesta) => {

        this.usuarios.set(
          respuesta.items,
        );

        this.total.set(
          respuesta.total,
        );

        this.pagina.set(
          respuesta.pagina,
        );

        this.porPagina.set(
          respuesta.por_pagina,
        );

        this.cargando.set(false);
      },

      error: (error: HttpErrorResponse) => {

        this.error.set(
          typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'No fue posible cargar los usuarios.',
        );

        this.cargando.set(false);
      },
    });
  }


  buscar(): void {

    this.pagina.set(1);

    this.cargarUsuarios();
  }


  limpiarFiltros(): void {

    this.formulario.reset({
      busqueda: '',
      estado: '',
    });

    this.pagina.set(1);

    this.cargarUsuarios();
  }


  paginaAnterior(): void {

    if (this.pagina() <= 1) {
      return;
    }

    this.pagina.update(
      pagina => pagina - 1,
    );

    this.cargarUsuarios();
  }


  paginaSiguiente(): void {

    const ultimaPagina =
      Math.ceil(
        this.total()
        / this.porPagina(),
      );

    if (
      this.pagina()
      >= ultimaPagina
    ) {
      return;
    }

    this.pagina.update(
      pagina => pagina + 1,
    );

    this.cargarUsuarios();
  }


  verDetalle(
    usuario: UsuarioResumenResponse,
  ): void {

    this.router.navigate([
      '/admin/usuarios',
      usuario.id_usuario,
    ]);
  }


  hayPaginaAnterior(): boolean {
    return this.pagina() > 1;
  }


  hayPaginaSiguiente(): boolean {

    return (
      this.pagina()
      * this.porPagina()
      < this.total()
    );
  }
}