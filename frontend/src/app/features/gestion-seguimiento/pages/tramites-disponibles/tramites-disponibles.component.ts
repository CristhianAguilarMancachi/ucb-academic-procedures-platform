import { IconoGestionComponent } from '../../components/icono-gestion/icono-gestion.component';
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import {
  GestionSeguimientoService,
  mensajeError,
} from '../../services/gestion-seguimiento.service';

import { ModalComponent } from '../../../../shared/components/modal/modal.component';

import {
  Condicion,
  Tramite,
} from '../../models/gestion-seguimiento.models';

import { AuthService } from '../../../../core/auth/auth.service';

@Component({
  selector: 'app-catalogo-tramites',
  standalone: true,

  imports: [
    IconoGestionComponent,
    CommonModule,
    RouterLink,
    ModalComponent,
  ],

  host: {
    class: 'm03-view',
  },

  templateUrl: './tramites-disponibles.component.html',
  styleUrl: './tramites-disponibles.component.scss',
})
export class TramitesDisponiblesComponent implements OnInit {
  private readonly api = inject(GestionSeguimientoService);

  private readonly route = inject(ActivatedRoute);

  private readonly router = inject(Router);

  readonly auth = inject(AuthService);

  readonly items = signal<Tramite[]>([]);

  readonly tramite = signal<Tramite | null>(null);

  readonly error = signal('');

  readonly ocupado = signal(false);

  detalleAbierto = false;

  seleccionar(id: number) {
    if (
      this.tramite()?.id_tramite === id ||
      this.ocupado()
    ) {
      return;
    }

    this.router.navigate([
      '/tramites',
      id,
    ]);
  }

  ngOnInit() {
    this.api.catalogo().subscribe({
      next: (r) => {
        this.items.set(r.items);
      },

      error: (e) => {
        this.fallar(e);
      },
    });

    this.route.paramMap.subscribe((params) => {
      const id = Number(
        params.get('id'),
      );

      this.ocupado.set(true);

      this.error.set('');

      this.tramite.set(null);

      if (id) {
        this.api.tramite(id).subscribe({
          next: (t) => {
            this.tramite.set(t);

            this.ocupado.set(false);
          },

          error: (e) => {
            this.fallar(e);
          },
        });

        return;
      }

      this.api.catalogo().subscribe({
        next: (r) => {
          this.items.set(r.items);

          this.ocupado.set(false);
        },

        error: (e) => {
          this.fallar(e);
        },
      });
    });
  }

  costosInformativos(t: Tramite) {
    const requisitos = t.id_tramite === 8
      ? this.requisitosPorTipo(t, false)
      : t.requisitos;

    return requisitos.filter(
      requisito => !!requisito.informacion_economica,
    );
  }

  condicion(c: Condicion) {
    return `${c.clave || c.campo} = ${c.valor}`;
  }

  requisitosPorTipo(t: Tramite, conclusion: boolean) {
    if (t.id_tramite !== 8) {
      return t.requisitos;
    }

    const nombreConclusion =
      'Certificado de Conclusión de Estudios';

    return t.requisitos.filter(requisito => {
      const regla = requisito.condicion;

      if (!regla) {
        return true;
      }

      if (
        regla.origen !== 'solicitud_dato' ||
        regla.clave !== 'tipo_certificado'
      ) {
        return false;
      }

      const coincide = regla.valor === nombreConclusion;

      if (regla.operador === 'igual') {
        return coincide === conclusion;
      }

      if (regla.operador === 'distinto') {
        return coincide !== conclusion;
      }

      return false;
    });
  }

  crear(t: Tramite) {
    if (
      this.ocupado() ||
      !t.permite_solicitudes ||
      !this.auth.tieneAlgunoDeLosRoles(['solicitante', 'administrador'])
    ) {
      return;
    }

    this.router.navigate(['/tramites', t.id_tramite, 'preparar']);
  }

  private fallar(
    e: Parameters<
      typeof mensajeError
    >[0],
  ) {
    this.error.set(
      mensajeError(e),
    );

    this.ocupado.set(false);
  }
}