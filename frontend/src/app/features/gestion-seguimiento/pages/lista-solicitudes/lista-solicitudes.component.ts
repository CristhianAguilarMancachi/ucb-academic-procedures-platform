import {
  Component,
  OnDestroy,
  OnInit,
  inject,
  signal,
} from '@angular/core';

import {
  CommonModule,
} from '@angular/common';

import {
  FormsModule,
} from '@angular/forms';

import {
  ActivatedRoute,
  RouterLink,
} from '@angular/router';

import {
  NgIcon,
  provideIcons,
} from '@ng-icons/core';

import {
  heroArrowsUpDown,
  heroCheckCircle,
  heroChevronDown,
  heroChevronRight,
  heroCog6Tooth,
  heroDocumentText,
  heroEye,
  heroMagnifyingGlass,
  heroPlus,
  heroXCircle,
} from '@ng-icons/heroicons/outline';

import {
  GestionSeguimientoService,
  mensajeError,
} from '../../services/gestion-seguimiento.service';

import {
  ESTADOS_FILTRO,
  SolicitudResumen,
  Tramite,
  etiquetaEstado,
} from '../../models/gestion-seguimiento.models';


@Component({
  selector:
    'app-solicitudes-lista',

  standalone:
    true,

  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    NgIcon,
  ],

  providers: [
    provideIcons({
      heroArrowsUpDown,
      heroCheckCircle,
      heroChevronDown,
      heroChevronRight,
      heroCog6Tooth,
      heroDocumentText,
      heroEye,
      heroMagnifyingGlass,
      heroPlus,
      heroXCircle,
    }),
  ],

  host: {
    class:
      'm03-view',
  },

  templateUrl:
    './lista-solicitudes.component.html',

  styleUrl:
    './lista-solicitudes.component.scss',
})
export class ListaSolicitudesComponent
  implements
    OnInit,
    OnDestroy
{
  private readonly api =
    inject(
      GestionSeguimientoService,
    );

  private readonly route =
    inject(
      ActivatedRoute,
    );


  /*
   * La ruta decide qué representación
   * de la bandeja se muestra.
   *
   * La autorización real continúa
   * en guards y backend.
   */
  readonly vistaAdministrativa =
    this.route
      .snapshot
      .data['admin']
      === true;


  readonly items =
    signal<
      SolicitudResumen[]
    >(
      [],
    );


  readonly tramitesFiltro =
    signal<
      Tramite[]
    >(
      [],
    );


  readonly error =
    signal(
      '',
    );


  readonly ocupado =
    signal(
      false,
    );


  readonly total =
    signal(
      0,
    );


  readonly etiqueta =
    etiquetaEstado;


  /*
   * lista_para_entrega se mantiene
   * como estado histórico en el modelo,
   * pero deja de mostrarse en ambos
   * listbox operativos.
   *
   * Borrador tampoco corresponde
   * a la bandeja administrativa.
   */
  readonly estados =
    ESTADOS_FILTRO.filter(
      (estado) =>
        !this.vistaAdministrativa ||
        estado !== 'borrador',
    );


  readonly pageSize =
    20;


  pagina =
    1;


  busqueda =
    '';


  orden:
    | 'recientes'
    | 'antiguos'
    | 'nombre' =
    'recientes';


  filtros = {
    estado:
      '',

    id_tramite:
      '',
  };


  private temporizadorBusqueda:
    ReturnType<
      typeof setTimeout
    > | null =
    null;


  ngOnInit(): void {
    if (
      this.vistaAdministrativa
    ) {
      this.api
        .catalogo()
        .subscribe({
          next: (
            respuesta,
          ) => {
            this.tramitesFiltro.set(
              respuesta.items,
            );
          },

          error: () => {
            /*
             * El catálogo de trámites
             * no debe bloquear la bandeja.
             */
            this.tramitesFiltro.set(
              [],
            );
          },
        });
    }

    this.cargar();
  }


  ngOnDestroy(): void {
    if (
      this.temporizadorBusqueda
    ) {
      clearTimeout(
        this.temporizadorBusqueda,
      );
    }
  }


  /*
   * En la bandeja administrativa,
   * el backend ya devuelve exactamente
   * los registros de la búsqueda.
   *
   * En Mis trámites se conserva
   * el filtro local ya existente.
   */
  visibles():
    SolicitudResumen[]
  {
    if (
      this.vistaAdministrativa
    ) {
      return this.items();
    }

    const q =
      this.busqueda
        .trim()
        .toLocaleLowerCase(
          'es',
        );

    const filtradas =
      this.items().filter(
        (
          solicitud,
        ) => {
          if (!q) {
            return true;
          }

          const nombre =
            this.nombreTramite(
              solicitud,
            );

          return `
            ${solicitud.id_solicitud}
            ${nombre}
          `
            .toLocaleLowerCase(
              'es',
            )
            .includes(
              q,
            );
        },
      );

    return [
      ...filtradas,
    ].sort(
      (
        a,
        b,
      ) => {
        if (
          this.orden ===
          'nombre'
        ) {
          return (
            this.nombreTramite(
              a,
            )
            .localeCompare(
              this.nombreTramite(
                b,
              ),
              'es',
            )
          );
        }

        const fechaA =
          new Date(
            this.fechaUltimaActualizacion(
              a,
            ),
          ).getTime();

        const fechaB =
          new Date(
            this.fechaUltimaActualizacion(
              b,
            ),
          ).getTime();

        if (
          this.orden ===
          'antiguos'
        ) {
          return (
            fechaA -
            fechaB
          );
        }

        return (
          fechaB -
          fechaA
        );
      },
    );
  }


  nombreTramite(
    solicitud:
      SolicitudResumen,
  ): string {
    return (
      solicitud
        .nombre_tramite_snapshot ||
      solicitud
        .nombre_tramite ||
      solicitud
        .tramite
        ?.nombre ||
      'Trámite académico'
    );
  }


  nombreSolicitante(
    solicitud:
      SolicitudResumen,
  ): string {
    return (
      solicitud
        .nombre_solicitante
        ?.trim() ||
      (
        solicitud
          .id_solicitante
          ? `Usuario #${solicitud.id_solicitante}`
          : 'Solicitante'
      )
    );
  }


  documentoSolicitante(
    solicitud:
      SolicitudResumen,
  ): string {
    const documento =
      solicitud
        .documento_identidad
        ?.trim();

    return (
      documento ||
      'No registrado'
    );
  }


  contar(
    estado:
      string,
  ): number {
    return (
      this.items()
        .filter(
          (
            solicitud,
          ) =>
            solicitud.estado
            === estado,
        )
        .length
    );
  }


  formatearNumeroSolicitud(
    id:
      number,
  ): string {
    return (
      String(
        id,
      )
      .padStart(
        4,
        '0',
      )
    );
  }


  fechaUltimaActualizacion(
    solicitud:
      SolicitudResumen,
  ): string {
    return (
      solicitud
        .fecha_actualizacion ||
      solicitud
        .fecha_envio ||
      solicitud
        .fecha_creacion
    );
  }


  etapaVisual(
    solicitud:
      SolicitudResumen,
  ): string {
    switch (
      solicitud.estado
    ) {
      case 'borrador':
        return (
          'Preparación'
        );

      case 'pendiente_recepcion':
        return (
          'Recepción'
        );

      case 'en_revision':
        return (
          'Revisión'
        );

      case 'en_proceso':
        return (
          'En proceso'
        );

      /*
       * Compatibilidad histórica.
       */
      case 'lista_para_entrega':
        return (
          'Entrega'
        );

      case 'finalizada':
        return (
          'Finalizada'
        );

      case 'cancelada':
        return (
          'Cancelada'
        );

      case 'rechazada':
        return (
          'Rechazada'
        );

      default:
        return (
          '—'
        );
    }
  }


  accionSiguiente(
    solicitud:
      SolicitudResumen,
  ): string {
    switch (
      solicitud.estado
    ) {
      case 'borrador':
        return (
          'Completar solicitud'
        );

      case 'pendiente_recepcion':
        return (
          'Esperar recepción'
        );

      case 'en_revision':
        return (
          'Esperar revisión'
        );

      case 'en_proceso':
        return (
          'Consultar seguimiento'
        );

      /*
       * Compatibilidad con solicitudes
       * creadas antes del cambio de flujo.
       */
      case 'lista_para_entrega':
        return (
          'Consultar indicaciones'
        );

      case 'finalizada':
        return (
          'Sin acciones pendientes'
        );

      case 'cancelada':

      case 'rechazada':
        return (
          'Solicitud cerrada'
        );

      default:
        return (
          'Consultar seguimiento'
        );
    }
  }


  textoAccionAdministrativa(
    solicitud:
      SolicitudResumen,
  ): string {
    if (
      solicitud.estado ===
        'finalizada' ||
      solicitud.estado ===
        'cancelada' ||
      solicitud.estado ===
        'rechazada'
    ) {
      return (
        'Ver'
      );
    }

    return (
      'Revisar'
    );
  }


  cargar(): void {
    this.ocupado.set(
      true,
    );

    this.error.set(
      '',
    );

    const filtros:
      Record<
        string,
        string |
        number |
        undefined
      > =
      this.vistaAdministrativa
        ? {
            estado:
              this.filtros
                .estado ||
              undefined,

            id_tramite:
              this.filtros
                .id_tramite ||
              undefined,

            busqueda:
              this.busqueda
                .trim() ||
              undefined,

            pagina:
              this.pagina,

            limite:
              this.pageSize,
          }
        : {
            estado:
              this.filtros
                .estado ||
              undefined,

            pagina:
              this.pagina,

            limite:
              this.pageSize,
          };

    this.api
      .listar(
        this.vistaAdministrativa,
        filtros,
      )
      .subscribe({
        next: (
          respuesta,
        ) => {
          this.items.set(
            respuesta.items,
          );

          this.total.set(
            respuesta.total,
          );

          this.ocupado.set(
            false,
          );
        },

        error: (
          e,
        ) => {
          this.error.set(
            mensajeError(
              e,
            ),
          );

          this.ocupado.set(
            false,
          );
        },
      });
  }


  /*
   * Los selects llaman directamente
   * a buscar().
   */
  buscar(): void {
    this.pagina =
      1;

    this.cargar();
  }


  /*
   * En administrativo la búsqueda
   * espera 350 ms antes de consultar
   * al backend.
   *
   * En solicitante no necesita
   * petición porque el filtro sigue
   * siendo local.
   */
  cambioBusqueda(): void {
    if (
      !this.vistaAdministrativa
    ) {
      return;
    }

    if (
      this.temporizadorBusqueda
    ) {
      clearTimeout(
        this.temporizadorBusqueda,
      );
    }

    this.temporizadorBusqueda =
      setTimeout(
        () => {
          this.pagina =
            1;

          this.cargar();
        },
        350,
      );
  }


  ejecutarBusqueda(): void {
    if (
      !this.vistaAdministrativa
    ) {
      return;
    }

    if (
      this.temporizadorBusqueda
    ) {
      clearTimeout(
        this.temporizadorBusqueda,
      );

      this.temporizadorBusqueda =
        null;
    }

    this.pagina =
      1;

    this.cargar();
  }


  mover(
    cambio:
      number,
  ): void {
    const destino =
      this.pagina +
      cambio;

    if (
      destino < 1 ||
      destino >
        this.totalPaginas()
    ) {
      return;
    }

    this.pagina =
      destino;

    this.cargar();
  }


  irPagina(
    pagina:
      number,
  ): void {
    if (
      pagina ===
        this.pagina ||
      pagina < 1 ||
      pagina >
        this.totalPaginas()
    ) {
      return;
    }

    this.pagina =
      pagina;

    this.cargar();
  }


  totalPaginas():
    number
  {
    return Math.max(
      1,

      Math.ceil(
        this.total() /
        this.pageSize,
      ),
    );
  }


  paginasVisibles():
    number[]
  {
    const total =
      this.totalPaginas();

    if (
      total <= 5
    ) {
      return (
        Array.from(
          {
            length:
              total,
          },

          (
            _,
            indice,
          ) =>
            indice + 1,
        )
      );
    }

    let inicio =
      Math.max(
        1,
        this.pagina - 2,
      );

    const fin =
      Math.min(
        total,
        inicio + 4,
      );

    inicio =
      Math.max(
        1,
        fin - 4,
      );

    return (
      Array.from(
        {
          length:
            fin -
            inicio +
            1,
        },

        (
          _,
          indice,
        ) =>
          inicio +
          indice,
      )
    );
  }


  inicioPagina():
    number
  {
    if (
      !this.total()
    ) {
      return 0;
    }

    return (
      (
        this.pagina -
        1
      ) *
      this.pageSize +
      1
    );
  }


  finPagina():
    number
  {
    return (
      Math.min(
        this.pagina *
        this.pageSize,

        this.total(),
      )
    );
  }
}