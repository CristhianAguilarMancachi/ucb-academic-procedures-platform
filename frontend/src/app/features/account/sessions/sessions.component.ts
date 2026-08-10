import {
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';

import { AccountService } from '../../../core/account/account.service';
import { AuthService } from '../../../core/auth/auth.service';
import {
  SesionResumenResponse,
} from '../../../core/account/account.models';

@Component({
  selector: 'app-sessions',
  standalone: true,
  imports: [
    CommonModule,
  ],
  templateUrl: './sessions.component.html',
  styleUrl: './sessions.component.scss',
})
export class SessionsComponent implements OnInit {

  private readonly accountService = inject(AccountService);
  private readonly authService = inject(AuthService);

  readonly sesiones =
    signal<SesionResumenResponse[]>([]);

  readonly cargando = signal(true);
  readonly procesando = signal(false);

  readonly error = signal<string | null>(null);
  readonly mensaje = signal<string | null>(null);

  readonly identificadorSesionActual =
    signal<string | null>(null);

  ngOnInit(): void {
    this.identificadorSesionActual.set(
      this.authService.obtenerIdentificadorSesionActual(),
    );

    this.cargarSesiones();
  }

  cargarSesiones(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.accountService.obtenerSesiones(true).subscribe({
      next: (respuesta) => {
        this.sesiones.set(respuesta.items);
        this.cargando.set(false);
      },

      error: () => {
        this.error.set(
          'No fue posible cargar las sesiones.',
        );

        this.cargando.set(false);
      },
    });
  }

  esSesionActual(
    sesion: SesionResumenResponse,
  ): boolean {
    return (
      sesion.identificador_sesion
      === this.identificadorSesionActual()
    );
  }

  estaActiva(
    sesion: SesionResumenResponse,
  ): boolean {
    return sesion.fecha_revocacion === null;
  }

  cerrarSesion(
    sesion: SesionResumenResponse,
  ): void {
    if (
      this.procesando()
      || this.esSesionActual(sesion)
    ) {
      return;
    }

    this.procesando.set(true);
    this.error.set(null);
    this.mensaje.set(null);

    this.accountService
      .cerrarSesion(sesion.id_sesion)
      .subscribe({
        next: () => {
          this.mensaje.set(
            'La sesión fue cerrada correctamente.',
          );

          this.cargarSesiones();
        },

        error: (error: HttpErrorResponse) => {
          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No fue posible cerrar la sesión.',
          );

          this.procesando.set(false);
        },

        complete: () => {
          this.procesando.set(false);
        },
      });
  }

  cerrarOtrasSesiones(): void {
    if (this.procesando()) {
      return;
    }

    this.procesando.set(true);
    this.error.set(null);
    this.mensaje.set(null);

    this.accountService
      .cerrarTodasLasSesiones({
        conservar_sesion_actual: true,
      })
      .subscribe({
        next: () => {
          this.mensaje.set(
            'Las demás sesiones fueron cerradas.',
          );

          this.cargarSesiones();
        },

        error: (error: HttpErrorResponse) => {
          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No fue posible cerrar las demás sesiones.',
          );

          this.procesando.set(false);
        },

        complete: () => {
          this.procesando.set(false);
        },
      });
  }
}