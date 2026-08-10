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
  Validators,
} from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';

import { AccountService } from '../../../core/account/account.service';
import {
  UsuarioAutenticadoResponse,
} from '../../../core/account/account.models';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
  ],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss',
})
export class ProfileComponent implements OnInit {

  private readonly fb = inject(FormBuilder);
  private readonly accountService = inject(AccountService);

  readonly usuario =
    signal<UsuarioAutenticadoResponse | null>(null);

  readonly cargando = signal(true);
  readonly guardando = signal(false);

  readonly error = signal<string | null>(null);
  readonly mensaje = signal<string | null>(null);

  readonly formulario = this.fb.nonNullable.group({
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
  });

  ngOnInit(): void {
    this.cargarPerfil();
  }

  cargarPerfil(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.accountService.obtenerPerfil().subscribe({
      next: (usuario) => {
        this.usuario.set(usuario);

        this.formulario.patchValue({
          nombres: usuario.nombres,
          apellidos: usuario.apellidos,
        });

        this.cargando.set(false);
      },

      error: () => {
        this.error.set(
          'No fue posible cargar la información del perfil.',
        );

        this.cargando.set(false);
      },
    });
  }

  guardarCambios(): void {
    if (
      this.formulario.invalid
      || this.guardando()
    ) {
      this.formulario.markAllAsTouched();
      return;
    }

    this.guardando.set(true);
    this.error.set(null);
    this.mensaje.set(null);

    this.accountService.actualizarPerfil(
      this.formulario.getRawValue(),
    ).subscribe({
      next: (usuario) => {
        this.usuario.set(usuario);

        this.mensaje.set(
          'Los datos del perfil fueron actualizados.',
        );

        this.guardando.set(false);
      },

      error: (error: HttpErrorResponse) => {
        this.error.set(
          typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'No fue posible actualizar el perfil.',
        );

        this.guardando.set(false);
      },
    });
  }

  obtenerCorreoPrincipal(): string {
    return (
      this.usuario()?.correos.find(
        (correo) => correo.es_principal,
      )?.correo
      ?? 'Sin correo principal'
    );
  }

  correoPrincipalVerificado(): boolean {
    return (
      this.usuario()?.correos.find(
        (correo) => correo.es_principal,
      )?.verificado
      ?? false
    );
  }
}