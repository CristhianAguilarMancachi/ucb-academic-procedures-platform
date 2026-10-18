
import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';

import { IconoGestionComponent } from '../icono-gestion/icono-gestion.component';
import { Historial } from '../../models/gestion-seguimiento.models';

type TipoEventoTimeline =
  | 'completado'
  | 'informativo'
  | 'advertencia'
  | 'cierre';

@Component({
  selector: 'app-gestion-timeline',
  standalone: true,
  imports: [
    IconoGestionComponent,
    DatePipe,
  ],
  host: {
    class: 'm03-view',
  },
  templateUrl: './timeline-solicitud.component.html',
  styleUrl: './timeline-solicitud.component.scss',
})
export class TimelineSolicitudComponent {
  readonly historial = input<Historial[]>([]);
  readonly administrativo = input(false);
  readonly detenida = input(false);

  etiquetaEvento(evento: string): string {
    const etiquetas: Record<string, string> = {
      solicitud_creada: 'Solicitud registrada',
      solicitud_registrada: 'Solicitud registrada',
      solicitud_enviada: 'Solicitud enviada',

      solicitud_recibida: 'Solicitud recibida',
      recepcion_registrada: 'Recepción administrativa',
      atencion_iniciada: 'Atención iniciada',
      procesamiento_iniciado: 'Procesamiento iniciado',

      entrega_fisica_declarada:
        'Entrega de documentación informada',
      documentacion_entregada:
        'Entrega de documentación informada',
      requisito_fisico_recibido:
        'Documentación física recibida',
      requisito_verificado:
        'Requisito verificado',

      factura_registrada: 'Factura registrada',
      pago_verificado: 'Pago verificado',
      pago_no_verificado: 'Pago no verificado',
      pago_verificacion_error:
        'No fue posible verificar el pago',
      verificar_pago_api_error:
        'No fue posible verificar el pago',

      observacion_registrada: 'Observación registrada',
      observacion_resuelta: 'Observación resuelta',

      resolucion_emitida: 'Resolución emitida',
      convocatoria_enviada: 'Convocatoria enviada',
      intervencion_convocada: 'Convocatoria presencial',
      firma_registrada: 'Firma registrada',
      conformidad_registrada: 'Conformidad registrada',
      conformidad_rechazada: 'Conformidad rechazada',

      resultado_registrado: 'Resultado registrado',
      lista_para_entrega: 'Documento listo para entrega',
      entrega_registrada: 'Entrega registrada',
      solicitud_finalizada: 'Trámite finalizado',

      solicitud_cancelada: 'Solicitud cancelada',
      solicitud_rechazada: 'Solicitud rechazada',

      // Eventos anteriores a la migración. Se conservan
      // con su significado original, sin reinterpretarlos
      // como firma o conformidad.
      etapa_iniciada: 'Etapa iniciada (histórico)',
      etapa_completada: 'Etapa completada (histórico)',
    };

    return (
      etiquetas[evento] ||
      evento
        .replaceAll('_', ' ')
        .replace(/^./, letra => letra.toUpperCase())
    );
  }

  tipoEvento(evento: string): TipoEventoTimeline {
    const cierres = new Set([
      'solicitud_cancelada',
      'solicitud_rechazada',
    ]);

    const advertencias = new Set([
      'observacion_registrada',
      'pago_no_verificado',
      'pago_verificacion_error',
      'verificar_pago_api_error',
      'conformidad_rechazada',
    ]);

    const informativos = new Set([
      'entrega_fisica_declarada',
      'documentacion_entregada',
      'procesamiento_iniciado',
      'atencion_iniciada',
      'etapa_iniciada',
      'lista_para_entrega',
      'factura_registrada',
      'convocatoria_enviada',
      'intervencion_convocada',
      'resolucion_emitida',
    ]);

    if (cierres.has(evento)) {
      return 'cierre';
    }

    if (advertencias.has(evento)) {
      return 'advertencia';
    }

    if (informativos.has(evento)) {
      return 'informativo';
    }

    return 'completado';
  }

  simboloEvento(evento: string): string {
    switch (this.tipoEvento(evento)) {
      case 'cierre':
        return '×';
      case 'advertencia':
        return '!';
      case 'informativo':
        return '•';
      default:
        return '✓';
    }
  }

  descripcionTipoEvento(evento: string): string {
    switch (this.tipoEvento(evento)) {
      case 'cierre':
        return 'Solicitud cerrada';
      case 'advertencia':
        return 'Requiere atención';
      case 'informativo':
        return 'Información registrada';
      default:
        return 'Hito completado';
    }
  }
}
