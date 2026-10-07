import { IconoGestionComponent } from '../../components/icono-gestion/icono-gestion.component';

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
  FormsModule,
} from '@angular/forms';

import {
  ActivatedRoute,
  RouterLink,
} from '@angular/router';

import {
  forkJoin,
  map,
  of,
  switchMap,
} from 'rxjs';

import {
  NgIcon,
  provideIcons,
} from '@ng-icons/core';

import {
  heroArrowLeft,
  heroChatBubbleLeftRight,
  heroDocumentText,
  heroExclamationTriangle,
  heroTicket,
} from '@ng-icons/heroicons/outline';

import {
  GestionSeguimientoService,
  mensajeError,
} from '../../services/gestion-seguimiento.service';

import {
  ModalComponent,
} from '../../../../shared/components/modal/modal.component';

import {
  TimelineSolicitudComponent,
} from '../../components/timeline-solicitud/timeline-solicitud.component';

import {
  Historial,
  Observacion,
  Requisito,
  Seguimiento,
  Solicitud,
  TipoFinalizacion,
  etiquetaEstado,
} from '../../models/gestion-seguimiento.models';


interface SolicitudConDocumentoPago
  extends Solicitud {
  documento_identidad_pago?:
    | string
    | null;
}


interface PagoVerificacionResultado {
  estado:
    | 'verificado'
    | 'no_verificado'
    | 'error';

  mensaje: string;
}


type AdminTab =
  | 'resumen'
  | 'requisitos'
  | 'historial';

type StudentRequirementTab =
  | 'documentos'
  | 'pago';


type EstadoPasoAdmin =
  | 'completado'
  | 'actual'
  | 'pendiente';


interface PasoAdmin {
  clave: string;
  titulo: string;
  detalle: string;
  estado: EstadoPasoAdmin;
}


@Component({
  selector:
    'app-solicitud-detalle',

  standalone: true,

  imports: [
    IconoGestionComponent,
    CommonModule,
    FormsModule,
    RouterLink,
    ModalComponent,
    TimelineSolicitudComponent,
    NgIcon,
  ],

  providers: [
    provideIcons({
      heroArrowLeft,
      heroChatBubbleLeftRight,
      heroDocumentText,
      heroExclamationTriangle,
      heroTicket,
    }),
  ],

  host: {
    class:
      'm03-view',
  },

  templateUrl:
    './seguimiento-solicitud.component.html',

  styleUrl:
    './seguimiento-solicitud.component.scss',
})
export class SeguimientoSolicitudComponent
  implements OnInit
{
  private readonly api =
    inject(
      GestionSeguimientoService,
    );

  private readonly route =
    inject(
      ActivatedRoute,
    );


  readonly admin =
    this.route.snapshot
      .data['admin'] ===
      true;


  readonly solicitud =
    signal<Solicitud | null>(
      null,
    );


  readonly seguimiento =
    signal<Seguimiento | null>(
      null,
    );


  readonly ocupado =
    signal(
      false,
    );


  readonly error =
    signal(
      '',
    );


  readonly mensaje =
    signal(
      '',
    );


  readonly etiqueta =
    etiquetaEstado;


  adminTab: AdminTab =
    'resumen';

  studentRequirementTab:
  StudentRequirementTab =
  'documentos';


  revisionResultado:
    | 'conforme'
    | 'correccion' =
    'conforme';


  revisionObservacion =
    '';


  modal:
    | 'cancelar'
    | 'rechazar'
    | 'resultado'
    | 'entrega'
    | 'fisico'
    | 'observacion'
    | 'entrega_estudiante'
    | null = null;


  requisitoFisico:
    | Requisito
    | null = null;


  confirmado =
    false;


  id =
    0;


  motivo =
    '';


  detalleResultado =
    '';


  tipoFinalizacion:
    | TipoFinalizacion
    | '' = '';


  receptor:
    | 'titular'
    | 'tercero' =
    'titular';


  nombreReceptor =
    '';


  documento =
    '';


  detalleEntrega =
    '';


  observacion = {
    detalle:
      '',

    correccion_requerida:
      '',

    canal_subsanacion:
      '',

    id_solicitud_requisito:
      null as number | null,

    id_solicitud_etapa:
      null as number | null,
  };


  facturas:
    Record<
      number,
      string
    > = {};


  verificaciones:
    Record<
      number,
      string
    > = {};


  ngOnInit() {
    this.id = Number(
      this.route.snapshot
        .paramMap
        .get(
          'id',
        ),
    );

    this.cargar();
  }


  // =========================================================
  // PRESENTACIÓN
  // =========================================================


  nombreTramite(
    solicitud: Solicitud,
  ): string {
    return (
      solicitud.nombre_tramite_snapshot ||
      solicitud.nombre_tramite ||
      solicitud.tramite?.nombre ||
      'Trámite académico'
    );
  }


  formatearNumeroSolicitud(
    id: number,
  ): string {
    return String(
      id,
    ).padStart(
      4,
      '0',
    );
  }


  fechaUltimaActualizacion(
    solicitud: Solicitud,
  ): string {
    return (
      solicitud.fecha_actualizacion ||
      solicitud.fecha_envio ||
      solicitud.fecha_creacion
    );
  }


  etiquetaPerfil(
    clave: string,
  ): string {
    const etiquetas: Record<
      string,
      string
    > = {
      codigo_estudiante:
        'Código de estudiante',

      sede:
        'Sede',

      carrera_programa:
        'Carrera o programa',

      nivel_academico:
        'Nivel académico',

      documento_identidad:
        'Documento de identidad',
    };

    return (
      etiquetas[
        clave
      ] ||
      clave.replaceAll(
        '_',
        ' ',
      )
    );
  }


  etiquetaFinalizacion(
    tipo: TipoFinalizacion,
  ): string {
    const etiquetas: Record<
      TipoFinalizacion,
      string
    > = {
      entrega:
        'Entrega o recojo',

      resultado_registrado:
        'Resultado registrado',

      externo:
        'Proceso externo',
    };

    return etiquetas[
      tipo
    ];
  }


  // =========================================================
  // MODALES
  // =========================================================


  abrir(
    modal:
      | 'cancelar'
      | 'rechazar'
      | 'resultado'
      | 'entrega'
      | 'fisico'
      | 'observacion'
      | 'entrega_estudiante',

    requisito:
      | Requisito
      | null = null,
  ) {
    this.modal =
      modal;

    this.requisitoFisico =
      requisito;

    this.confirmado =
      false;

    this.motivo =
      '';

    this.error.set(
      '',
    );

    this.mensaje.set(
      '',
    );

    if (
      modal ===
      'observacion'
    ) {
      this.observacion = {
        detalle:
          '',

        correccion_requerida:
          '',

        canal_subsanacion:
          '',

        id_solicitud_requisito:
          null,

        id_solicitud_etapa:
          null,
      };
    }

    if (
      modal ===
      'fisico'
    ) {
      this.revisionResultado =
        'conforme';

      this.revisionObservacion =
        '';
    }

    if (
      modal ===
      'resultado'
    ) {
      this.detalleResultado =
        '';

      this.tipoFinalizacion =
        '';
    }

    if (
      modal ===
      'entrega'
    ) {
      this.receptor =
        'titular';

      this.nombreReceptor =
        '';

      this.documento =
        '';

      this.detalleEntrega =
        '';
    }
  }


  cerrarModal() {
    if (
      !this.ocupado()
    ) {
      this.modal =
        null;

      this.confirmado =
        false;

      this.requisitoFisico =
        null;
    }
  }


  // =========================================================
  // FLUJO
  // =========================================================


  etapas() {
    return (
      (
        this.admin
          ? this.solicitud()
              ?.etapas
          : this.seguimiento()
              ?.etapas
      )
      ||
      []
    );
  }


  etapaEnCurso() {
    const solicitud =
      this.solicitud();

    return (
      solicitud?.etapas?.some(
        (etapa) =>
          etapa.id_solicitud_etapa ===
            solicitud.id_etapa_actual &&
          etapa.estado ===
            'en_curso',
      )
      ||
      false
    );
  }


  resultadoDisponible() {
    const solicitud =
      this.solicitud();

    if (
      !solicitud ||
      !this.admin
    ) {
      return false;
    }

    const etapas =
      solicitud.etapas ||
      [];

    return (
      (
        solicitud.estado ===
          'en_proceso'
        ||
        (
          solicitud.estado ===
            'en_revision' &&
          etapas.length ===
            0
        )
      )
      &&
      etapas.every(
        (etapa) =>
          etapa.estado ===
          'completada',
      )
    );
  }


  pendientes() {
    return this.obs()
      .filter(
        (observacion) =>
          observacion.estado ===
          'pendiente',
      )
      .length;
  }


  // =========================================================
  // CARGA
  // =========================================================


  cargar(
    limpiarMensajes = true,
  ) {
    this.ocupado.set(
      true,
    );

    if (
      limpiarMensajes
    ) {
      this.error.set(
        '',
      );

      this.mensaje.set(
        '',
      );
    }

    const consulta =
      this.admin
        ? this.api
            .detalle(
              this.id,
              true,
            )
            .pipe(
              map(
                (solicitud) => ({
                  s:
                    solicitud,

                  seguimiento:
                    null as Seguimiento | null,
                }),
              ),
            )
        : forkJoin({
            s:
              this.api.detalle(
                this.id,
              ),

            seguimiento:
              this.api.seguimiento(
                this.id,
              ),
          });

    consulta.subscribe({
      next: (resultado) => {
        this.solicitud.set(
          resultado.s,
        );

        this.seguimiento.set(
          resultado.seguimiento,
        );

        if (
          !this.admin
        ) {
          this.ajustarPestanaRequisitosSolicitante();
        }

        resultado.s.requisitos.forEach(
          (requisito) => {
            this.facturas[
              requisito.id_solicitud_requisito
            ] =
              requisito.numero_factura
              ||
              '';
          },
        );

        this.ocupado.set(
          false,
        );
      },

      error: (e) =>
        this.fallar(
          e,
        ),
    });
  }


  // =========================================================
  // REQUISITOS ADMINISTRATIVOS
  // =========================================================


  editable(
    requisito: Requisito,
  ): boolean {
    const solicitud =
      this.solicitud();

    return (
      !!solicitud
      &&
      [
        'en_revision',
        'en_proceso',
      ].includes(
        solicitud.estado,
      )
      &&
      (
        requisito.id_solicitud_etapa ===
          null
        ||
        (
          solicitud.estado ===
            'en_proceso'
          &&
          requisito.id_solicitud_etapa ===
            solicitud.id_etapa_actual
        )
      )
    );
  }


  etapaRequisito(
    requisito: Requisito,
  ): string {
    if (
      requisito.id_solicitud_etapa ===
      null
    ) {
      return (
        'Requisito inicial'
      );
    }

    if (
      !this.admin
    ) {
      return (
        requisito.puede_registrar_factura
        ||
        requisito.puede_declarar_entrega
      )
        ? 'Disponible en la etapa actual'
        : 'Se habilitará en una etapa posterior';
    }

    return (
      this.solicitud()
        ?.etapas
        ?.find(
          (etapa) =>
            etapa.id_solicitud_etapa ===
            requisito.id_solicitud_etapa,
        )
        ?.nombre
      ||
      'Etapa del proceso'
    );
  }


  // =========================================================
  // CANCELACIÓN
  // =========================================================


  cancelable():
    boolean {
    const solicitud =
      this.solicitud();

    return (
      !!solicitud
      &&
      [
        'borrador',
        'pendiente_recepcion',
      ].includes(
        solicitud.estado,
      )
      &&
      !solicitud.requisitos.some(
        (requisito) =>
          !!requisito.numero_factura,
      )
    );
  }


  // =========================================================
  // OBSERVACIONES / HISTORIAL
  // =========================================================


  obs():
    Observacion[] {
    return (
      (
        this.admin
          ? this.solicitud()
              ?.observaciones
          : this.seguimiento()
              ?.observaciones
      )
      ||
      []
    );
  }


  historial():
    Historial[] {
    return (
      (
        this.admin
          ? this.solicitud()
              ?.historial
          : this.seguimiento()
              ?.historial
      )
      ||
      []
    );
  }


  // =========================================================
  // ACCIONES DEL SOLICITANTE
  // =========================================================


  documentoPago(): string {
    return (
      (this.solicitud() as SolicitudConDocumentoPago | null)
        ?.documento_identidad_pago
      ||
      ''
    );
  }


  requisitosEconomicos():
    Requisito[] {
    return (
      this.solicitud()
        ?.requisitos
        .filter(
          (requisito) =>
            !!requisito.concepto_economico,
        )
      ||
      []
    );
  }


  requisitosFisicos():
    Requisito[] {
    return (
      this.solicitud()
        ?.requisitos
        .filter(
          (requisito) =>
            requisito.requiere_presentacion_fisica,
        )
      ||
      []
    );
  }


  requisitosFisicosDeclarables():
    Requisito[] {
    return this.requisitosFisicos()
      .filter(
        (requisito) =>
          requisito.puede_declarar_entrega
          &&
          !requisito.presentado
          &&
          !requisito.entrega_declarada,
      );
  }

  tieneDocumentosSolicitante():
    boolean {
    return (
      this.requisitosFisicos()
        .length >
      0
    );
  }


  tienePagoSolicitante():
    boolean {
    return (
      this.requisitosEconomicos()
        .length >
      0
    );
  }


  mostrarTabsRequisitosSolicitante():
    boolean {
    return (
      this.tieneDocumentosSolicitante()
      &&
      this.tienePagoSolicitante()
    );
  }


  seleccionarPestanaRequisitoSolicitante(
    tab: StudentRequirementTab,
  ) {
    if (
      tab === 'documentos'
      &&
      !this.tieneDocumentosSolicitante()
    ) {
      return;
    }

    if (
      tab === 'pago'
      &&
      !this.tienePagoSolicitante()
    ) {
      return;
    }

    this.studentRequirementTab =
      tab;
  }


  private ajustarPestanaRequisitosSolicitante() {
    if (
      this.admin
    ) {
      return;
    }

    const tieneDocumentos =
      this.tieneDocumentosSolicitante();

    const tienePago =
      this.tienePagoSolicitante();

    if (
      tieneDocumentos
      &&
      !this.todosDocumentosRecibidos()
    ) {
      this.studentRequirementTab =
        'documentos';

      return;
    }

    if (
      tienePago
      &&
      this.requisitosEconomicos()
        .some(
          (requisito) =>
            requisito.estado_verificacion !==
            'cumple',
        )
    ) {
      this.studentRequirementTab =
        'pago';

      return;
    }

    if (
      tieneDocumentos
    ) {
      this.studentRequirementTab =
        'documentos';

      return;
    }

    this.studentRequirementTab =
      'pago';
  }


  todosDocumentosRecibidos():
    boolean {
    const requisitos =
      this.requisitosFisicos();

    return (
      requisitos.length >
        0
      &&
      requisitos.every(
        (requisito) =>
          requisito.presentado,
      )
    );
  }


  hayDocumentosDeclaradosPendientes():
    boolean {
    return this.requisitosFisicos()
      .some(
        (requisito) =>
          requisito.entrega_declarada
          &&
          !requisito.presentado,
      );
  }


  tieneAccionesRequisitos():
    boolean {
    return (
      this.requisitosEconomicos()
        .length >
        0
      ||
      this.requisitosFisicos()
        .length >
        0
    );
  }


  estadoPago(
    requisito: Requisito,
  ): string {
    if (
      requisito.estado_verificacion ===
      'cumple'
    ) {
      return (
        'Pago verificado'
      );
    }

    if (
      requisito.estado_verificacion ===
      'no_cumple'
    ) {
      return (
        'No verificado'
      );
    }

    if (
      requisito.puede_registrar_factura
    ) {
      return (
        'Pendiente de verificación'
      );
    }

    return (
      'Disponible más adelante'
    );
  }


  estadoDocumento(
    requisito: Requisito,
  ): string {
    if (
      requisito.presentado
    ) {
      return (
        'Recibido'
      );
    }

    if (
      requisito.entrega_declarada
    ) {
      return (
        'Entrega informada'
      );
    }

    if (
      requisito.puede_declarar_entrega
    ) {
      return (
        'Pendiente de entrega'
      );
    }

    return (
      'Disponible más adelante'
    );
  }


  // =========================================================
  // VERIFICACIÓN DE PAGO
  // =========================================================


  verificarPago(
    requisito: Requisito,
  ) {
    const numeroFactura =
      this.facturas[
        requisito.id_solicitud_requisito
      ]?.trim();

    if (
      !numeroFactura
    ) {
      this.error.set(
        'Ingresa el número de factura antes de verificar el pago.',
      );

      this.mensaje.set(
        '',
      );

      return;
    }

    if (
      !this.documentoPago()
    ) {
      this.error.set(
        'No se encontró un documento de identidad para verificar el pago.',
      );

      this.mensaje.set(
        '',
      );

      return;
    }

    this.ocupado.set(
      true,
    );

    this.error.set(
      '',
    );

    this.mensaje.set(
      '',
    );

    this.api
      .factura(
        this.id,

        requisito
          .id_solicitud_requisito,

        numeroFactura,
      )
      .pipe(
        switchMap(
          () =>
            this.api.post<
              PagoVerificacionResultado
            >(
              (
                `solicitudes/${this.id}/requisitos/`
                +
                `${requisito.id_solicitud_requisito}/verificar-pago`
              ),
            ),
        ),
      )
      .subscribe({
        next: (resultado) => {
          if (
            resultado.estado ===
            'verificado'
          ) {
            this.error.set(
              '',
            );

            this.mensaje.set(
              resultado.mensaje,
            );
          } else {
            /*
             * Una verificación fallida NO es un mensaje
             * de éxito.
             *
             * Al recargar la solicitud, la propia tarjeta
             * de pago mostrará el estado no_cumple.
             */
            this.mensaje.set(
              '',
            );

            this.error.set(
              resultado.mensaje,
            );
          }

          /*
           * Conservamos el mensaje mientras volvemos
           * a cargar el estado real del requisito.
           */
          this.cargar(
            false,
          );
        },

        error: (e) =>
          this.fallar(
            e,
          ),
      });
  }


  // =========================================================
  // DECLARACIÓN DE DOCUMENTACIÓN
  // =========================================================


  declararDocumentos() {
    const requisitos =
      this.requisitosFisicosDeclarables();

    if (
      !requisitos.length
      ||
      !this.confirmado
      ||
      this.ocupado()
    ) {
      return;
    }

    this.ocupado.set(
      true,
    );

    this.error.set(
      '',
    );

    this.mensaje.set(
      '',
    );

    forkJoin(
      requisitos.map(
        (requisito) =>
          this.api.post<Solicitud>(
            (
              `solicitudes/${this.id}/requisitos/`
              +
              `${requisito.id_solicitud_requisito}/declaracion-fisica`
            ),
          ),
      ),
    )
      .subscribe({
        next: () => {
          this.modal =
            null;

          this.confirmado =
            false;

          this.mensaje.set(
            requisitos.length ===
              1
              ? (
                  'Entrega de documentación informada. ' +
                  'Queda pendiente la recepción por personal administrativo.'
                )
              : (
                  'Entrega de documentación informada. ' +
                  'Los documentos quedan pendientes de recepción ' +
                  'por personal administrativo.'
                ),
          );

          this.cargar(
            false,
          );
        },

        error: (e) =>
          this.fallar(
            e,
          ),
      });
  }


  // =========================================================
  // ACCIONES GENERALES
  // =========================================================


  accion(
    path: string,
    datos: unknown = {},
  ) {
    this.ocupado.set(
      true,
    );

    this.error.set(
      '',
    );

    this.mensaje.set(
      '',
    );

    this.api
      .post<{
        mensaje?: string;
      }>(
        `${
          this.admin
            ? 'admin/'
            : ''
        }solicitudes/${
          this.id
        }/${path}`,

        datos,
      )
      .subscribe({
        next: (resultado) => {
          this.modal =
            null;

          this.mensaje.set(
            resultado.mensaje
            ||
            '',
          );

          this.motivo =
            '';

          this.observacion = {
            detalle:
              '',

            correccion_requerida:
              '',

            canal_subsanacion:
              '',

            id_solicitud_etapa:
              null,

            id_solicitud_requisito:
              null,
          };

          this.cargar(
            false,
          );
        },

        error: (e) =>
          this.fallar(
            e,
          ),
      });
  }


  verificar(
    requisito: Requisito,
    estado: string,
  ) {
    this.accion(
      (
        `requisitos/`
        +
        `${requisito.id_solicitud_requisito}`
        +
        `/verificar`
      ),

      {
        estado,

        detalle:
          this.verificaciones[
            requisito.id_solicitud_requisito
          ]?.trim()
          ||
          null,
      },
    );
  }


  crearObservacion() {
    this.accion(
      'observaciones',

      {
        ...this.observacion,

        canal_subsanacion:
          this.observacion
            .canal_subsanacion
            .trim()
          ||
          null,
      },
    );
  }


  finalizar() {
    this.accion(
      'finalizar',

      {
        detalle:
          this.detalleResultado
            .trim()
          ||
          null,

        tipo_finalizacion:
          this.solicitud()
            ?.tipo_finalizacion
            ? null
            : (
                this.tipoFinalizacion
                ||
                null
              ),
      },
    );
  }


  entregar() {
    this.accion(
      'entregar',

      {
        receptor:
          this.receptor,

        nombre_receptor:
          this.nombreReceptor
            .trim()
          ||
          null,

        documento_identidad:
          this.documento
            .trim()
          ||
          null,

        detalle:
          this.detalleEntrega
            .trim()
          ||
          null,
      },
    );
  }



  // =========================================================
  // NUEVA EXPERIENCIA ADMINISTRATIVA
  // =========================================================


  seleccionarAdminTab(
    tab: AdminTab,
  ) {
    this.adminTab =
      tab;
  }


  tieneRequisitosPrevios():
    boolean {
    return (
      this.requisitosFisicos()
        .length >
        0
      ||
      this.requisitosEconomicos()
        .length >
        0
    );
  }


  documentosFisicosConformes():
    boolean {
    const requisitos =
      this.requisitosFisicos();

    return (
      requisitos.length >
        0
      &&
      requisitos.every(
        (requisito) =>
          requisito.presentado
          &&
          requisito.estado_verificacion ===
            'cumple',
      )
    );
  }


  pagosVerificados():
    boolean {
    const requisitos =
      this.requisitosEconomicos();

    return (
      requisitos.length ===
        0
      ||
      requisitos.every(
        (requisito) =>
          requisito.estado_verificacion ===
            'cumple',
      )
    );
  }


  requisitosCompletos():
    boolean {
    const fisicos =
      this.requisitosFisicos();

    const fisicosOk =
      fisicos.length ===
        0
      ||
      this.documentosFisicosConformes();

    return (
      fisicosOk
      &&
      this.pagosVerificados()
    );
  }


  pasosAdministrativos(
    solicitud: Solicitud,
  ): PasoAdmin[] {
    const pasos:
      PasoAdmin[] = [];

    pasos.push({
      clave:
        'solicitud',
      titulo:
        'Solicitud enviada',
      detalle:
        solicitud.fecha_envio
          ? new Date(
              solicitud.fecha_envio,
            ).toLocaleDateString(
              'es-BO',
            )
          : 'Registrada',
      estado:
        solicitud.estado ===
          'borrador'
          ? 'actual'
          : 'completado',
    });

    if (
      this.tieneRequisitosPrevios()
    ) {
      const requisitosListos =
        this.requisitosCompletos();

      const enRevision =
        [
          'pendiente_recepcion',
          'en_revision',
        ].includes(
          solicitud.estado,
        );

      pasos.push({
        clave:
          'requisitos',
        titulo:
          this.requisitosFisicos()
            .length
            ? 'Revisión de requisitos'
            : 'Verificación de requisitos',
        detalle:
          requisitosListos
            ? 'Completados'
            : (
                enRevision
                  ? 'En proceso'
                  : 'Pendiente'
              ),
        estado:
          requisitosListos
            ? 'completado'
            : (
                enRevision
                  ? 'actual'
                  : 'pendiente'
              ),
      });
    }

    const finalizada =
      solicitud.estado ===
        'finalizada';

    const procesando =
      [
        'en_proceso',
        'lista_para_entrega',
      ].includes(
        solicitud.estado,
      );

    pasos.push({
      clave:
        'proceso',
      titulo:
        'En procesamiento',
      detalle:
        finalizada
          ? 'Completado'
          : (
              procesando
                ? 'En proceso'
                : 'Pendiente'
            ),
      estado:
        finalizada
          ? 'completado'
          : (
              procesando
                ? 'actual'
                : 'pendiente'
            ),
    });

    pasos.push({
      clave:
        'final',
      titulo:
        'Finalizado',
      detalle:
        finalizada
          ? 'Completado'
          : 'Pendiente',
      estado:
        finalizada
          ? 'completado'
          : 'pendiente',
    });

    return pasos;
  }


  mensajePasoActual(
    solicitud: Solicitud,
  ): string {
    if (
      solicitud.estado ===
      'finalizada'
    ) {
      return (
        'El trámite concluyó y ya no requiere acciones administrativas.'
      );
    }

    if (
      [
        'cancelada',
        'rechazada',
      ].includes(
        solicitud.estado,
      )
    ) {
      return (
        'La solicitud está cerrada. El historial permanece disponible para consulta.'
      );
    }

    if (
      this.requisitosFisicos()
        .length
      &&
      !this.documentosFisicosConformes()
    ) {
      if (
        this.hayDocumentosDeclaradosPendientes()
      ) {
        return (
          'Revisa en conjunto la documentación física declarada por el solicitante.'
        );
      }

      return (
        'La documentación física aún no fue informada como entregada por el solicitante.'
      );
    }

    if (
      !this.pagosVerificados()
    ) {
      return (
        'El trámite está a la espera de la verificación automática del pago.'
      );
    }

    if (
      solicitud.estado ===
        'en_proceso'
    ) {
      return (
        'El trámite se encuentra en procesamiento. Solo registra una acción cuando exista una incidencia o el resultado final esté listo.'
      );
    }

    return (
      'La solicitud está lista para continuar con su procesamiento administrativo.'
    );
  }


  textoResultadoFinal(
    solicitud: Solicitud,
  ): string {
    switch (
      solicitud.tipo_finalizacion
    ) {
      case 'entrega':
        return (
          'Documento disponible para recojo'
        );

      case 'resultado_registrado':
        return (
          'Resultado o resolución registrada'
        );

      case 'externo':
        return (
          'Proceso externo concluido'
        );

      default:
        return (
          'Resultado final del trámite'
        );
    }
  }


  carreraPrograma(
    solicitud: Solicitud,
  ): string {
    return (
      solicitud.perfil_academico
        ?.['carrera_programa']
      ||
      'No registrada'
    );
  }


  historialAdministrativo():
    Historial[] {
    const tecnicos =
      new Set([
        'etapa_iniciada',
        'etapa_completada',
        'requisito_verificado',
      ]);

    return this.historial()
      .filter(
        (item) =>
          !tecnicos.has(
            item.evento,
          ),
      )
      .slice(
        -6,
      );
  }


  tituloHistorial(
    evento: string,
  ): string {
    const etiquetas:
      Record<string, string> = {
      solicitud_creada:
        'Solicitud registrada',

      solicitud_registrada:
        'Solicitud registrada',

      solicitud_enviada:
        'Solicitud enviada',

      entrega_fisica_declarada:
        'Entrega de documentación informada',

      documentacion_entregada:
        'Entrega de documentación informada',

      solicitud_recibida:
        'Solicitud recibida',

      procesamiento_iniciado:
        'Procesamiento iniciado',

      solicitud_finalizada:
        'Trámite finalizado',

      solicitud_rechazada:
        'Solicitud rechazada',

      solicitud_cancelada:
        'Solicitud cancelada',

      observacion_registrada:
        'Observación registrada',
    };

    return (
      etiquetas[
        evento
      ]
      ||
      evento
        .replaceAll(
          '_',
          ' ',
        )
        .replace(
          /^\w/,
          (letra) =>
            letra.toUpperCase(),
        )
    );
  }


  puedeRevisarDocumentacion():
    boolean {
    const solicitud =
      this.solicitud();

    return (
      !!solicitud
      &&
      [
        'pendiente_recepcion',
        'en_revision',
      ].includes(
        solicitud.estado,
      )
      &&
      this.requisitosFisicos()
        .length >
        0
      &&
      this.hayDocumentosDeclaradosPendientes()
    );
  }


  puedeContinuarProcesamiento(
    solicitud: Solicitud,
  ): boolean {
    return (
      solicitud.estado ===
        'en_revision'
      &&
      this.requisitosCompletos()
      &&
      !!solicitud.etapas
        ?.length
    );
  }


  abrirRevisionDocumentacion() {
    this.abrir(
      'fisico',
    );
  }


  guardarRevisionDocumentacion() {
    const solicitud =
      this.solicitud();

    const requisitos =
      this.requisitosFisicos();

    if (
      !solicitud
      ||
      !requisitos.length
      ||
      this.ocupado()
    ) {
      return;
    }

    this.ocupado.set(
      true,
    );

    this.error.set(
      '',
    );

    this.mensaje.set(
      '',
    );

    const registrarPresentacion =
      requisitos.map(
        (requisito) =>
          requisito.presentado
            ? of(
                null,
              )
            : this.api.post(
                (
                  `admin/solicitudes/${this.id}/requisitos/`
                  +
                  `${requisito.id_solicitud_requisito}/presentacion`
                ),
              ),
      );

    forkJoin(
      registrarPresentacion,
    )
      .pipe(
        switchMap(
          () => {
            if (
              this.revisionResultado ===
              'correccion'
            ) {
              const detalle =
                this.revisionObservacion
                  .trim();

              if (
                !detalle
              ) {
                throw new Error(
                  'La observación es obligatoria cuando se requiere una corrección.',
                );
              }

              return this.api.post(
                `admin/solicitudes/${this.id}/observaciones`,
                {
                  detalle,
                  correccion_requerida:
                    detalle,
                  canal_subsanacion:
                    'Presentación física en Kardex',
                  id_solicitud_requisito:
                    null,
                  id_solicitud_etapa:
                    solicitud.id_etapa_actual
                    ||
                    null,
                },
              );
            }

            return forkJoin(
              requisitos.map(
                (requisito) =>
                  this.api.post(
                    (
                      `admin/solicitudes/${this.id}/requisitos/`
                      +
                      `${requisito.id_solicitud_requisito}/verificar`
                    ),
                    {
                      estado:
                        'cumple',
                      detalle:
                        null,
                    },
                  ),
              ),
            );
          },
        ),
        switchMap(
          () => {
            if (
              this.revisionResultado !==
                'conforme'
              ||
              solicitud.estado !==
                'en_revision'
              ||
              !solicitud.etapas
                ?.length
            ) {
              return of(
                null,
              );
            }

            /*
             * Mientras el backend conserva la acción /iniciar,
             * el frontend la encadena automáticamente para que
             * el personal administrativo no tenga que hacer un
             * segundo clic después de una revisión conforme.
             */
            return this.api.post(
              `admin/solicitudes/${this.id}/iniciar`,
              {},
            );
          },
        ),
      )
      .subscribe({
        next: () => {
          this.modal =
            null;

          this.revisionObservacion =
            '';

          this.ocupado.set(
            false,
          );

          this.cargar(
            false,
          );
        },

        error: (e) => {
          if (
            e instanceof Error
            &&
            !('status' in e)
          ) {
            this.error.set(
              e.message,
            );

            this.ocupado.set(
              false,
            );

            return;
          }

          this.fallar(
            e as Parameters<
              typeof mensajeError
            >[0],
          );
        },
      });
  }


  // =========================================================
  // ERRORES
  // =========================================================


  private fallar(
    e: Parameters<
      typeof mensajeError
    >[0],
  ) {
    this.mensaje.set(
      '',
    );

    this.error.set(
      mensajeError(
        e,
      ),
    );

    this.ocupado.set(
      false,
    );
  }
}
