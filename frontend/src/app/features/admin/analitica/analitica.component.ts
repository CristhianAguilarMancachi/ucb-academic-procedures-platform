
import {
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AnaliticaService } from './analitica.service';
import {
  AnaliticaResponse,
  PeriodoAnalitica,
  TramiteAnalitica,
} from './analitica.models';

type TipoSerie = 'recibidas' | 'concluidas';

@Component({
  selector: 'app-analitica',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './analitica.component.html',
  styleUrl: './analitica.component.scss',
})
export class AnaliticaComponent implements OnInit {
  private readonly api = inject(AnaliticaService);
  private readonly destroyRef = inject(DestroyRef);

  readonly datos = signal<AnaliticaResponse | null>(null);
  readonly tramites = signal<TramiteAnalitica[]>([]);
  readonly cargando = signal(false);
  readonly error = signal('');
  readonly mostrarDetalles = signal(false);

  periodo: PeriodoAnalitica = '30_dias';
  idTramite: number | null = null;

  readonly maximoTop = computed(() =>
    Math.max(
      1,
      ...(this.datos()?.top_tramites.map(t => t.cantidad) ?? [])
    )
  );

  readonly maximoSolicitudes = computed(() => {
    const series = this.datos()?.evolucion_solicitudes ?? [];

    return Math.max(
      1,
      ...series.flatMap(p => [
        p.recibidas,
        p.concluidas ?? 0,
      ])
    );
  });

  readonly maximoRag = computed(() =>
    Math.max(
      1,
      ...(this.datos()?.evolucion_rag.map(p => p.consultas) ?? [])
    )
  );

  ngOnInit(): void {
    this.actualizar();
  }

  actualizar(): void {
    if (this.cargando()) return;

    this.cargando.set(true);
    this.error.set('');

    this.api
      .consultar(this.periodo, this.idTramite)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: respuesta => {
          this.datos.set(respuesta);
          this.tramites.set(respuesta.tramites);
          this.cargando.set(false);
        },
        error: () => {
          this.error.set(
            'No se pudieron cargar los indicadores. Intenta consultar nuevamente.'
          );
          this.cargando.set(false);
        },
      });
  }

  nombreAmbito(datos: AnaliticaResponse): string {
    return datos.tramites.find(
      t => t.id_tramite === datos.filtros.id_tramite
    )?.nombre ?? 'Todos los trámites';
  }

  porcentaje(valor: number, maximo: number): number {
    return maximo > 0
      ? Math.max(0, Math.min(100, valor / maximo * 100))
      : 0;
  }

  // Coordenadas para el gráfico SVG de solicitudes.
  // Los valores nulos no se dibujan como ceros.
  private coordenadas(
    valores: (number | null)[],
    maximo: number
  ): string[] {
    const inicioX = 45;
    const finX = 755;
    const inicioY = 15;
    const finY = 162;

    const segmentos: string[] = [];
    let segmento: string[] = [];

    valores.forEach((valor, indice) => {
      if (valor === null) {
        if (segmento.length) {
          segmentos.push(segmento.join(' '));
        }
        segmento = [];
        return;
      }

      const x = valores.length === 1
        ? (inicioX + finX) / 2
        : inicioX +
          (indice / (valores.length - 1)) *
          (finX - inicioX);

      const y = finY -
        (Math.max(0, valor) / Math.max(1, maximo)) *
        (finY - inicioY);

      segmento.push(
        `${x.toFixed(2)},${y.toFixed(2)}`
      );
    });

    if (segmento.length) {
      segmentos.push(segmento.join(' '));
    }

    return segmentos;
  }

  lineasSolicitudes(tipo: TipoSerie): string[] {
    const datos = this.datos();
    if (!datos) return [];

    return this.coordenadas(
      datos.evolucion_solicitudes.map(p => p[tipo]),
      this.maximoSolicitudes()
    );
  }

  xPunto(indice: number, total: number): number {
    if (total <= 1) return 400;
    return 45 + (indice / (total - 1)) * 710;
  }

  yPunto(valor: number, maximo: number): number {
    return 162 -
      (Math.max(0, valor) / Math.max(1, maximo)) * 147;
  }

  mostrarEtiqueta(indice: number, total: number): boolean {
    if (total <= 6) return true;

    const salto = Math.ceil(total / 5);

    return indice === 0 ||
      indice === total - 1 ||
      indice % salto === 0;
  }

  etiquetaPeriodo(fecha: string): string {
    const partes = fecha.slice(0, 10).split('-');

    if (partes.length !== 3) return fecha;

    return `${partes[2]}/${partes[1]}`;
  }

  haySolicitudes(datos: AnaliticaResponse): boolean {
    return datos.evolucion_solicitudes.some(
      punto => punto.recibidas > 0 ||
        (punto.concluidas ?? 0) > 0
    );
  }

  hayConsultasRag(datos: AnaliticaResponse): boolean {
    return datos.evolucion_rag.some(
      punto => punto.consultas > 0
    );
  }
}
