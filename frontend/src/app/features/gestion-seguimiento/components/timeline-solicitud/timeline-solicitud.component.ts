import {
  IconoGestionComponent,
} from '../icono-gestion/icono-gestion.component';

import {
  Component,
  input,
} from '@angular/core';

import {
  DatePipe,
} from '@angular/common';

import {
  Etapa,
  Historial,
  etiquetaEstado,
} from '../../models/gestion-seguimiento.models';


type TipoEventoTimeline =
  | 'completado'
  | 'informativo'
  | 'advertencia'
  | 'cierre';


@Component({
  selector:
    'app-gestion-timeline',

  standalone: true,

  imports: [
    IconoGestionComponent,
    DatePipe,
  ],

  host: {
    class:
      'm03-view',
  },

  templateUrl:
    './timeline-solicitud.component.html',

  styleUrl:
    './timeline-solicitud.component.scss',
})
export class TimelineSolicitudComponent {
  readonly historial =
    input<Historial[]>([]);

  readonly etapas =
    input<Etapa[]>([]);

  readonly administrativo =
    input(false);

  readonly detenida =
    input(false);

  readonly etiqueta =
    etiquetaEstado;


  // =========================================================
  // ETIQUETAS DEL HISTORIAL
  // =========================================================


  etiquetaEvento(
    evento: string,
  ): string {
    const etiquetas:
      Record<string, string> = {
      solicitud_creada:
        'Solicitud registrada',

      solicitud_enviada:
        'Solicitud enviada',

      solicitud_recibida:
        'Solicitud recibida',

      recepcion_registrada:
        'Solicitud recibida',

      entrega_fisica_declarada:
        'Entrega de documentación informada',

      requisito_fisico_recibido:
        'Documentación física recibida',

      pago_verificado:
        'Pago verificado',

      procesamiento_iniciado:
        'Procesamiento iniciado',

      etapa_iniciada:
        'Etapa iniciada',

      etapa_completada:
        'Etapa completada',

      observacion_registrada:
        'Observación registrada',

      observacion_resuelta:
        'Observación resuelta',

      resultado_registrado:
        'Resultado registrado',

      lista_para_entrega:
        'Disponible para entrega',

      entrega_registrada:
        'Entrega registrada',

      solicitud_finalizada:
        'Finalización del trámite',

      solicitud_cancelada:
        'Solicitud cancelada',

      solicitud_rechazada:
        'Solicitud rechazada',

      /*
       * Estos dos eventos ya no deberían llegar
       * al seguimiento público con el backend actual.
       *
       * Se conservan únicamente por compatibilidad
       * con registros históricos o vista administrativa.
       */
      factura_registrada:
        'Factura registrada',

      pago_no_verificado:
        'Pago no acreditado',

      pago_verificacion_error:
        'No fue posible verificar el pago',

      verificar_pago_api_error:
        'No fue posible verificar el pago',
    };

    return (
      etiquetas[evento]
      ||
      evento
        .replaceAll(
          '_',
          ' ',
        )
        .replace(
          /^./,
          (letra) =>
            letra.toUpperCase(),
        )
    );
  }


  // =========================================================
  // SIGNIFICADO VISUAL DE CADA EVENTO
  // =========================================================


  tipoEvento(
    evento: string,
  ): TipoEventoTimeline {
    /*
     * CIERRE NEGATIVO
     *
     * Rojo únicamente para estados que realmente
     * cierran negativamente la solicitud.
     */
    if (
      evento ===
        'solicitud_cancelada'
      ||
      evento ===
        'solicitud_rechazada'
    ) {
      return (
        'cierre'
      );
    }


    /*
     * ADVERTENCIA / ACCIÓN REQUERIDA
     *
     * Las observaciones no significan que todo
     * el trámite haya fallado, por eso utilizamos
     * amarillo y no rojo.
     *
     * Los eventos antiguos de pagos fallidos
     * también entran aquí únicamente para
     * compatibilidad administrativa.
     */
    if (
      evento ===
        'observacion_registrada'
      ||
      evento ===
        'pago_no_verificado'
      ||
      evento ===
        'pago_verificacion_error'
      ||
      evento ===
        'verificar_pago_api_error'
    ) {
      return (
        'advertencia'
      );
    }


    /*
     * INFORMACIÓN / PROCESO ACTUAL
     *
     * Estos eventos registran algo importante,
     * pero todavía no representan una validación
     * o conclusión definitiva.
     *
     * El caso principal es:
     *
     * entrega_fisica_declarada
     *
     * porque el estudiante solamente informó
     * que hizo la entrega; todavía falta que
     * Personal Administrativo la reciba.
     */
    if (
      evento ===
        'entrega_fisica_declarada'
      ||
      evento ===
        'procesamiento_iniciado'
      ||
      evento ===
        'etapa_iniciada'
      ||
      evento ===
        'lista_para_entrega'
      ||
      evento ===
        'factura_registrada'
    ) {
      return (
        'informativo'
      );
    }


    /*
     * HITOS COMPLETADOS
     *
     * Todo lo restante corresponde a acciones
     * que efectivamente quedaron realizadas.
     */
    return (
      'completado'
    );
  }


  simboloEvento(
    evento: string,
  ): string {
    const tipo =
      this.tipoEvento(
        evento,
      );

    switch (
      tipo
    ) {
      case 'cierre':
        return '×';

      case 'advertencia':
        return '!';

      case 'informativo':
        return '•';

      case 'completado':
      default:
        return '✓';
    }
  }


  descripcionTipoEvento(
    evento: string,
  ): string {
    const tipo =
      this.tipoEvento(
        evento,
      );

    switch (
      tipo
    ) {
      case 'cierre':
        return (
          'Solicitud cerrada'
        );

      case 'advertencia':
        return (
          'Requiere atención'
        );

      case 'informativo':
        return (
          'Información registrada'
        );

      case 'completado':
      default:
        return (
          'Hito completado'
        );
    }
  }


  // =========================================================
  // ETAPAS
  // =========================================================


  descripcionEstadoEtapa(
    estado: string,
  ): string {
    switch (
      estado
    ) {
      case 'completada':
        return (
          'Etapa completada.'
        );

      case 'en_curso':
        return (
          'Etapa actual del trámite.'
        );

      case 'pendiente':
        return (
          'Pendiente de procesamiento.'
        );

      default:
        return etiquetaEstado(
          estado,
        );
    }
  }
}