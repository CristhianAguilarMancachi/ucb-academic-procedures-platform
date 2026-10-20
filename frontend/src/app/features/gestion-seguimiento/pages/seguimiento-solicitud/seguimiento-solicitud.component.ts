// RETIRO_ENTREGA_FISICA_13F
import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import {
  forkJoin,
  from,
  of,
  switchMap,
  concatMap,
  toArray,
  timer,
} from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NgIcon, provideIcons } from '@ng-icons/core';

import {
  heroArrowLeft,
  heroChatBubbleLeftRight,
  heroDocumentText,
  heroExclamationTriangle,
  heroTicket,
} from '@ng-icons/heroicons/outline';

import { IconoGestionComponent } from '../../components/icono-gestion/icono-gestion.component';
import { ModalComponent } from '../../../../shared/components/modal/modal.component';
import { TimelineSolicitudComponent } from '../../components/timeline-solicitud/timeline-solicitud.component';

import {
  GestionSeguimientoService,
  mensajeError,
} from '../../services/gestion-seguimiento.service';

import {
  Dato,
  Historial,
  Observacion,
  Requisito,
  Seguimiento,
  Solicitud,
  TipoFinalizacion,
  ValorDato,
  etiquetaEstado,
} from '../../models/gestion-seguimiento.models';

type AdminTab = 'resumen' | 'requisitos' | 'actividad';
type StudentRequirementTab = 'documentos' | 'pago';
type EstadoPasoAdmin = 'completado' | 'actual' | 'pendiente';

type ModalSeguimiento =
  | 'cancelar'
  | 'rechazar'
  | 'resultado'
  | 'fisico'
  | 'observacion'
  | 'entrega_estudiante'
  | 'resolucion'
  | 'convocatoria'
  | 'intervencion'
  | 'reenviar'
  | 'verificar_requisito'
  | 'confirmar_administrativos'
  | null;

type ResultadoRevision = 'firmada' | 'conforme' | 'no_conforme';
type EstadoVerificacion = 'cumple' | 'no_cumple';

interface PasoAdmin {
  clave: string;
  titulo: string;
  detalle: string;
  estado: EstadoPasoAdmin;
}

interface IntervencionPresencial {
  id_intervencion: number;
  id_solicitud: number;
  tipo: 'firma' | 'conformidad';
  estado: 'convocada' | 'firmada' | 'conforme' | 'no_conforme' | 'anulada';
  fecha_convocatoria?: string | null;
  fecha_revision?: string | null;
  motivo_desacuerdo?: string | null;
}

interface NotificacionSolicitud {
  id_notificacion: number;
  id_intervencion?: number | null;
  tipo?: string;
  estado: string;
  destinatario?: string;
  asunto?: string;
  fecha_envio?: string | null;
}

interface ResolucionEmitida {
  id_historial: number;
  id_solicitud: number;
  id_usuario_actor: number | null;
  fecha_emision: string;
  detalle: string;
}

interface PagoVerificacionResultado {
  estado: 'verificado' | 'no_verificado' | 'error';
  mensaje: string;
}

interface UnidadSubsanacion {
  id_unidad: number;
  nombre: string;
}

@Component({
  selector: 'app-solicitud-detalle',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    ModalComponent,
    TimelineSolicitudComponent,
    IconoGestionComponent,
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
  templateUrl: './seguimiento-solicitud.component.html',
  styleUrl: './seguimiento-solicitud.component.scss',
})
export class SeguimientoSolicitudComponent implements OnInit {
  private readonly api = inject(GestionSeguimientoService);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private avisoSecuencia = 0;

  readonly admin = this.route.snapshot.data['admin'] === true;
  readonly solicitud = signal<Solicitud | null>(null);
  readonly seguimiento = signal<Seguimiento | null>(null);
  readonly intervenciones = signal<IntervencionPresencial[]>([]);
  readonly notificaciones = signal<NotificacionSolicitud[]>([]);
  readonly resolucion = signal<ResolucionEmitida | null>(null);

  readonly ocupado = signal(false);
  readonly error = signal('');
  readonly mensaje = signal('');
  readonly etiqueta = etiquetaEstado;

  id = 0;

  adminTab: AdminTab = 'resumen';
  studentRequirementTab: StudentRequirementTab = 'documentos';

  modal: ModalSeguimiento = null;
  confirmado = false;
  motivo = '';

  requisitoFisico: Requisito | null = null;
  requisitoSeleccionado: Requisito | null = null;

  estadoRequisito: EstadoVerificacion = 'cumple';
  detalleVerificacion = '';

  revisionResultado: 'conforme' | 'correccion' = 'conforme';
  revisionObservacion = '';
  documentosSeleccionados: Record<number, boolean> = {};
  administrativosSeleccionados: Record<number, boolean> = {};
  detalleConfirmacionAdministrativa = '';

  detalleResultado = '';
  tipoFinalizacion: TipoFinalizacion | '' = '';

  fechaRevision = '';
  resultadoIntervencion: ResultadoRevision = 'conforme';
  motivoDesacuerdo = '';

  idNotificacionReenvio = 0;

  observacion = this.nuevaObservacion();

  readonly unidadesSubsanacion = signal<UnidadSubsanacion[]>([]);
  readonly cargandoUnidadesSubsanacion = signal(false);
  readonly errorUnidadesSubsanacion = signal('');

  canalSubsanacionSeleccionado = '';
  canalSubsanacionPersonalizado = '';

  facturas: Record<number, string> = {};
  verificaciones: Record<number, string> = {};

  ngOnInit(): void {
    this.id = Number(this.route.snapshot.paramMap.get('id'));

    if (!Number.isInteger(this.id) || this.id <= 0) {
      this.error.set(
        'El identificador de la solicitud no es válido.'
      );
      return;
    }

    this.cargar();
  }

  private nuevaObservacion() {
    return {
      detalle: '',
      correccion_requerida: '',
      canal_subsanacion: '',
      id_solicitud_requisito: null as number | null,
    };
  }

  cargarUnidadesSubsanacion(): void {
    if (!this.admin) {
      return;
    }

    this.cargandoUnidadesSubsanacion.set(true);
    this.errorUnidadesSubsanacion.set('');

    this.api
      .get<UnidadSubsanacion[]>(
        'admin/solicitudes/unidades-subsanacion'
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: unidades => {
          this.unidadesSubsanacion.set(
            unidades.filter(
              unidad =>
                Number.isInteger(unidad.id_unidad) &&
                !!unidad.nombre?.trim()
            )
          );
          this.cargandoUnidadesSubsanacion.set(false);
        },
        error: () => {
          this.unidadesSubsanacion.set([]);
          this.errorUnidadesSubsanacion.set(
            'No se pudieron consultar las unidades registradas. ' +
            'Puedes escribir el canal manualmente.'
          );
          this.canalSubsanacionSeleccionado = '__otra__';
          this.cargandoUnidadesSubsanacion.set(false);
        },
      });
  }

  seleccionarCanalSubsanacion(valor: string): void {
    this.canalSubsanacionSeleccionado = valor;

    if (valor === '__otra__') {
      this.observacion.canal_subsanacion =
        this.canalSubsanacionPersonalizado.trim();
    } else {
      this.observacion.canal_subsanacion = valor;
    }
  }

  private canalSubsanacionActual(): string | null {
    const valor = this.canalSubsanacionSeleccionado === '__otra__'
      ? this.canalSubsanacionPersonalizado.trim()
      : this.canalSubsanacionSeleccionado.trim();

    return valor || null;
  }

  private fechaLocal(): string {
    const fecha = new Date();

    return [
      fecha.getFullYear(),
      String(fecha.getMonth() + 1).padStart(2, '0'),
      String(fecha.getDate()).padStart(2, '0'),
    ].join('-');
  }

  private informarError(error: HttpErrorResponse): void {
    this.mensaje.set('');
    this.error.set(mensajeError(error));
    this.ocupado.set(false);
  }

  private mostrarAvisoExito(texto: string): void {
    const secuencia = ++this.avisoSecuencia;

    this.mensaje.set(texto);

    timer(6000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (
          secuencia === this.avisoSecuencia &&
          this.mensaje() === texto
        ) {
          this.mensaje.set('');
        }
      });
  }

  private actualizarTrasAccion(mensaje: string): void {
    this.modal = null;
    this.confirmado = false;
    this.requisitoSeleccionado = null;
    this.requisitoFisico = null;
    this.motivo = '';
    this.observacion = this.nuevaObservacion();

    this.mostrarAvisoExito(mensaje);
    this.cargar(false);
  }

  // =========================================================
  // CARGA DE LA SOLICITUD
  // =========================================================

  cargar(limpiarMensajes = true): void {
    if (!Number.isInteger(this.id) || this.id <= 0) {
      return;
    }

    this.ocupado.set(true);

    if (limpiarMensajes) {
      this.error.set('');
      this.mensaje.set('');
    }

    if (this.admin) {
      forkJoin({
        solicitud: this.api.detalle(this.id, true),
        intervenciones: this.api.get<IntervencionPresencial[]>(
          `admin/solicitudes/${this.id}/intervenciones`
        ),
        notificaciones: this.api.get<NotificacionSolicitud[]>(
          `admin/solicitudes/${this.id}/notificaciones`
        ),
      })
        .pipe(
          switchMap(resultado => {
            if (
              resultado.solicitud.tipo_intervencion !== 'firma'
            ) {
              return of({
                ...resultado,
                resolucion: null as ResolucionEmitida | null,
              });
            }

            return this.api
              .get<ResolucionEmitida | null>(
                `admin/solicitudes/${this.id}/resolucion`
              )
              .pipe(
                switchMap(resolucion =>
                  of({
                    ...resultado,
                    resolucion,
                  })
                )
              );
          })
        )
        .subscribe({
          next: resultado => {
            this.solicitud.set(resultado.solicitud);
            this.seguimiento.set(null);
            this.intervenciones.set(resultado.intervenciones);
            this.notificaciones.set(resultado.notificaciones);
            this.resolucion.set(resultado.resolucion);

            this.sincronizarFacturas(resultado.solicitud);
            this.ocupado.set(false);
          },
          error: error => this.informarError(error),
        });

      return;
    }

    forkJoin({
      solicitud: this.api.detalle(this.id),
      seguimiento: this.api.seguimiento(this.id),
    }).subscribe({
      next: ({ solicitud, seguimiento }) => {
        this.solicitud.set(solicitud);
        this.seguimiento.set(seguimiento);
        this.intervenciones.set([]);
        this.notificaciones.set([]);
        this.resolucion.set(null);

        this.sincronizarFacturas(solicitud);
        this.ajustarPestanaRequisitosSolicitante();
        this.ocupado.set(false);
      },
      error: error => this.informarError(error),
    });
  }

  private sincronizarFacturas(solicitud: Solicitud): void {
    this.facturas = {};

    for (const requisito of solicitud.requisitos || []) {
      this.facturas[requisito.id_solicitud_requisito] =
        requisito.numero_factura || '';
    }
  }

  // =========================================================
  // PRESENTACIÓN DE DATOS
  // =========================================================

  nombreTramite(s: Solicitud): string {
    return (
      s.nombre_tramite_snapshot ||
      s.nombre_tramite ||
      s.tramite?.nombre ||
      'Trámite académico'
    );
  }

  formatearNumeroSolicitud(id: number): string {
    return String(id).padStart(4, '0');
  }

  fechaUltimaActualizacion(s: Solicitud): string {
    return (
      s.fecha_actualizacion ||
      s.fecha_envio ||
      s.fecha_creacion
    );
  }

  etiquetaPerfil(clave: string): string {
    const etiquetas: Record<string, string> = {
      codigo_estudiante: 'Código de estudiante',
      sede: 'Sede',
      carrera_programa: 'Carrera o programa',
      nivel_academico: 'Nivel académico',
      documento_identidad: 'Documento de identidad',
    };

    return etiquetas[clave] || clave.replaceAll('_', ' ');
  }

  etiquetaFinalizacion(tipo: TipoFinalizacion): string {
    const etiquetas: Record<TipoFinalizacion, string> = {
      entrega: 'Entrega o recojo',
      resultado_registrado: 'Resultado registrado',
      externo: 'Proceso externo',
    };

    return etiquetas[tipo];
  }

  etiquetaIntervencion(): string {
    switch (this.solicitud()?.tipo_intervencion) {
      case 'firma':
        return 'Firma presencial';

      case 'conformidad':
        return 'Conformidad presencial';

      default:
        return 'Sin intervención presencial';
    }
  }

  mostrarValor(
    valor: ValorDato | null | undefined
  ): string {
    if (valor === true) {
      return 'Sí';
    }

    if (valor === false) {
      return 'No';
    }

    if (
      valor === null ||
      valor === undefined ||
      valor === ''
    ) {
      return 'No registrado';
    }

    return String(valor);
  }

  datosFormulario(): Dato[] {
    return this.solicitud()?.datos || [];
  }

  tieneDatosFormulario(): boolean {
    return this.datosFormulario().length > 0;
  }

  datosPerfil(): { clave: string; valor: string }[] {
    const perfil =
      this.solicitud()?.perfil_academico || {};

    return Object.entries(perfil).map(
      ([clave, valor]) => ({
        clave,
        valor: valor || 'No registrado',
      })
    );
  }

  carreraPrograma(s: Solicitud): string {
    return (
      s.perfil_academico?.['carrera_programa'] ||
      'No registrada'
    );
  }

  textoResultadoFinal(s: Solicitud): string {
    switch (s.tipo_finalizacion) {
      case 'entrega':
        return 'Documento disponible para recojo';

      case 'resultado_registrado':
        return 'Resultado registrado';

      case 'externo':
        return 'Proceso externo concluido';

      default:
        return 'Pendiente de definir';
    }
  }

  // =========================================================
  // OBSERVACIONES E HISTORIAL
  // =========================================================

  obs(): Observacion[] {
    return (
      (
        this.admin
          ? this.solicitud()?.observaciones
          : this.seguimiento()?.observaciones
      ) || []
    );
  }

  historial(): Historial[] {
    return (
      (
        this.admin
          ? this.solicitud()?.historial
          : this.seguimiento()?.historial
      ) || []
    );
  }

  pendientes(): number {
    return this.obs().filter(
      observacion =>
        observacion.estado === 'pendiente'
    ).length;
  }

  historialAdministrativo(): Historial[] {
    return this.historial().slice(-6);
  }

  tituloHistorial(evento: string): string {
    const etiquetas: Record<string, string> = {
      solicitud_creada: 'Solicitud registrada',
      solicitud_registrada: 'Solicitud registrada',
      solicitud_enviada: 'Solicitud enviada',
      solicitud_recibida: 'Solicitud recibida',
      recepcion_registrada: 'Recepción registrada',
      requisito_fisico_recibido: 'Documento físico recibido',
      atencion_iniciada: 'Atención iniciada',
      procesamiento_iniciado: 'Procesamiento iniciado',
      entrega_fisica_declarada: 'Entrega informada',
      documentacion_entregada: 'Entrega informada',
      requisito_verificado: 'Requisito verificado',
      requisito_administrativo_confirmado: 'Requisito administrativo confirmado',
      resolucion_emitida: 'Resolución emitida',
      convocatoria_preparada: 'Convocatoria preparada',
      firma_presencial_registrada: 'Firma registrada',
      conformidad_presencial_registrada: 'Conformidad registrada',
      revision_sin_conformidad: 'Sin conformidad',
      resultado_registrado: 'Resultado registrado',
      lista_para_entrega: 'Lista para entrega',
      entrega_registrada: 'Entrega registrada',
      solicitud_finalizada: 'Solicitud finalizada',
      observacion_registrada: 'Observación registrada',
      observacion_resuelta: 'Observación resuelta',
      solicitud_cancelada: 'Solicitud cancelada',
      solicitud_rechazada: 'Solicitud rechazada',
      etapa_iniciada: 'Etapa iniciada (histórico)',
      etapa_completada: 'Etapa completada (histórico)',
    };

    return (
      etiquetas[evento] ||
      evento
        .replaceAll('_', ' ')
        .replace(
          /^./,
          letra => letra.toUpperCase()
        )
    );
  }

  // =========================================================
  // REQUISITOS
  // =========================================================

  todosRequisitos(): Requisito[] {
    return this.solicitud()?.requisitos || [];
  }

  requisitosEconomicos(): Requisito[] {
    return this.todosRequisitos().filter(
      requisito => !!requisito.concepto_economico
    );
  }

  requisitosFisicos(): Requisito[] {
    return this.todosRequisitos().filter(
      requisito => requisito.requiere_presentacion_fisica
    );
  }

  requisitosOrdinarios(): Requisito[] {
    return this.todosRequisitos().filter(
      requisito =>
        !requisito.concepto_economico &&
        !requisito.requiere_presentacion_fisica
    );
  }

  requisitosAdministrativosPendientes(): Requisito[] {
    return this.requisitosOrdinarios().filter(
      requisito => requisito.estado_verificacion !== 'cumple'
    );
  }

  puedeConfirmarAdministrativos(): boolean {
    return (
      this.admin &&
      !this.ocupado() &&
      ['en_revision', 'en_proceso'].includes(this.solicitud()?.estado || '') &&
      this.requisitosAdministrativosPendientes().length > 0
    );
  }

  abrirConfirmacionAdministrativa(): void {
    if (!this.puedeConfirmarAdministrativos()) {
      return;
    }
    this.abrir('confirmar_administrativos');
  }

  administrativosMarcados(): Requisito[] {
    return this.requisitosAdministrativosPendientes().filter(
      requisito => this.administrativosSeleccionados[requisito.id_solicitud_requisito] === true
    );
  }

  seleccionarTodosAdministrativos(seleccionar: boolean): void {
    if (this.ocupado()) return;
    for (const requisito of this.requisitosAdministrativosPendientes()) {
      this.administrativosSeleccionados[requisito.id_solicitud_requisito] = seleccionar;
    }
  }

  guardarConfirmacionAdministrativa(): void {
    if (!this.puedeConfirmarAdministrativos()) return;
    const ids_requisitos = this.administrativosMarcados().map(
      requisito => requisito.id_solicitud_requisito
    );
    if (!ids_requisitos.length) {
      this.error.set('Selecciona al menos un requisito administrativo.');
      return;
    }
    this.accion('requisitos/administrativos/confirmar', {
      ids_requisitos,
      detalle: this.detalleConfirmacionAdministrativa.trim() || null,
    });
  }

  requisitosObligatorios(): Requisito[] {
    return this.todosRequisitos().filter(
      requisito => requisito.obligatorio
    );
  }

  requisitosCompletos(): boolean {
    return this.requisitosObligatorios().every(
      requisito =>
        requisito.estado_verificacion === 'cumple' &&
        (
          !requisito.requiere_presentacion_fisica ||
          requisito.presentado
        )
    );
  }

  cantidadRequisitosCompletos(): number {
    return this.requisitosObligatorios().filter(
      requisito =>
        requisito.estado_verificacion === 'cumple' &&
        (
          !requisito.requiere_presentacion_fisica ||
          requisito.presentado
        )
    ).length;
  }

  cantidadRequisitosPendientes(): number {
    return (
      this.requisitosObligatorios().length -
      this.cantidadRequisitosCompletos()
    );
  }

  documentosFisicosConformes(): boolean {
    return this.requisitosFisicos().every(
      requisito =>
        requisito.presentado &&
        requisito.estado_verificacion === 'cumple'
    );
  }

  pagosVerificados(): boolean {
    return this.requisitosEconomicos().every(
      requisito =>
        requisito.estado_verificacion === 'cumple'
    );
  }

  tieneRequisitosPrevios(): boolean {
    return this.todosRequisitos().length > 0;
  }

  tieneAccionesRequisitos(): boolean {
    return (
      this.requisitosEconomicos().length > 0 ||
      this.requisitosFisicos().length > 0
    );
  }

  editable(requisito: Requisito): boolean {
    const estado = this.solicitud()?.estado;

    return (
      this.admin &&
      !this.ocupado() &&
      ['en_revision', 'en_proceso'].includes(estado || '') &&
      !requisito.concepto_economico
    );
  }

  etapaRequisito(_requisito: Requisito): string {
    return 'Requisito del trámite';
  }

  puedeVerificarIndividual(requisito: Requisito): boolean {
    return this.editable(requisito);
  }

  puedeVerificarPagoAdmin(requisito: Requisito): boolean {
    return (
      this.admin &&
      !this.ocupado() &&
      ['en_revision', 'en_proceso'].includes(
        this.solicitud()?.estado || ''
      ) &&
      !!requisito.concepto_economico &&
      requisito.estado_verificacion !== 'cumple' &&
      !!requisito.numero_factura
    );
  }

  estadoRequisitoTexto(requisito: Requisito): string {
    if (requisito.estado_verificacion === 'cumple') {
      return 'Verificado';
    }

    if (requisito.estado_verificacion === 'no_cumple') {
      return 'No cumple';
    }

    return 'Pendiente';
  }

  abrirVerificacionIndividual(requisito: Requisito): void {
    if (!this.puedeVerificarIndividual(requisito)) {
      return;
    }

    this.requisitoSeleccionado = requisito;

    this.estadoRequisito =
      requisito.estado_verificacion === 'no_cumple'
        ? 'no_cumple'
        : 'cumple';

    this.detalleVerificacion = '';

    this.abrir('verificar_requisito');
  }

  guardarVerificacionIndividual(): void {
    const requisito = this.requisitoSeleccionado;

    if (
      !requisito ||
      !this.puedeVerificarIndividual(requisito)
    ) {
      return;
    }

    if (
      this.estadoRequisito === 'cumple' &&
      requisito.requiere_presentacion_fisica &&
      !requisito.presentado
    ) {
      this.error.set(
        'Primero registra la recepción física del documento.'
      );
      return;
    }

    if (
      this.estadoRequisito === 'no_cumple' &&
      !this.detalleVerificacion.trim()
    ) {
      this.error.set(
        'Describe por qué el requisito no cumple.'
      );
      return;
    }

    this.verificar(
      requisito,
      this.estadoRequisito,
      this.detalleVerificacion.trim()
    );
  }

  verificar(
    requisito: Requisito,
    estado: string,
    detalle?: string
  ): void {
    if (!this.puedeVerificarIndividual(requisito)) {
      return;
    }

    if (
      estado !== 'cumple' &&
      estado !== 'no_cumple'
    ) {
      this.error.set(
        'Selecciona un resultado válido.'
      );
      return;
    }

    if (
      estado === 'cumple' &&
      requisito.requiere_presentacion_fisica &&
      !requisito.presentado
    ) {
      this.error.set(
        'El documento físico todavía no fue recibido.'
      );
      return;
    }

    this.accion(
      `requisitos/${requisito.id_solicitud_requisito}/verificar`,
      {
        estado,
        detalle:
          detalle ||
          this.verificaciones[
            requisito.id_solicitud_requisito
          ]?.trim() ||
          null,
      }
    );
  }

  verificarPagoAdministrativo(
    requisito: Requisito
  ): void {
    if (!this.puedeVerificarPagoAdmin(requisito)) {
      return;
    }

    this.accion(
      `requisitos/${requisito.id_solicitud_requisito}/verificar-pago`
    );
  }

  // =========================================================
  // REQUISITOS DEL SOLICITANTE
  // =========================================================

  documentoPago(): string {
    return (
      this.solicitud()?.documento_identidad_pago || ''
    );
  }

  requisitosFisicosDeclarables(): Requisito[] {
    return this.requisitosFisicos().filter(
      requisito =>
        requisito.puede_declarar_entrega &&
        !requisito.presentado &&
        !requisito.entrega_declarada
    );
  }

  tieneDocumentosSolicitante(): boolean {
    return this.requisitosFisicos().length > 0;
  }

  tienePagoSolicitante(): boolean {
    return this.requisitosEconomicos().length > 0;
  }

  mostrarTabsRequisitosSolicitante(): boolean {
    return (
      this.tieneDocumentosSolicitante() &&
      this.tienePagoSolicitante()
    );
  }

  seleccionarPestanaRequisitoSolicitante(
    tab: StudentRequirementTab
  ): void {
    if (
      tab === 'documentos' &&
      !this.tieneDocumentosSolicitante()
    ) {
      return;
    }

    if (
      tab === 'pago' &&
      !this.tienePagoSolicitante()
    ) {
      return;
    }

    this.studentRequirementTab = tab;
  }

  private ajustarPestanaRequisitosSolicitante(): void {
    if (this.admin) {
      return;
    }

    if (
      this.tieneDocumentosSolicitante() &&
      !this.todosDocumentosRecibidos()
    ) {
      this.studentRequirementTab = 'documentos';
    } else if (
      this.tienePagoSolicitante() &&
      this.requisitosEconomicos().some(
        requisito =>
          requisito.estado_verificacion !== 'cumple'
      )
    ) {
      this.studentRequirementTab = 'pago';
    } else {
      this.studentRequirementTab =
        this.tieneDocumentosSolicitante()
          ? 'documentos'
          : 'pago';
    }
  }

  todosDocumentosRecibidos(): boolean {
    const requisitos = this.requisitosFisicos();

    return (
      requisitos.length > 0 &&
      requisitos.every(requisito => requisito.presentado)
    );
  }

  hayDocumentosDeclaradosPendientes(): boolean {
    return this.requisitosFisicos().some(
      requisito =>
        requisito.entrega_declarada &&
        !requisito.presentado
    );
  }

  estadoPago(requisito: Requisito): string {
    if (requisito.estado_verificacion === 'cumple') {
      return 'Pago verificado';
    }

    if (requisito.estado_verificacion === 'no_cumple') {
      return 'No verificado';
    }

    return requisito.puede_registrar_factura
      ? 'Pendiente de verificación'
      : 'No disponible';
  }

  estadoDocumento(requisito: Requisito): string {
    if (requisito.presentado) {
      return 'Recibido';
    }

    if (requisito.entrega_declarada) {
      return 'Entrega informada';
    }

    return requisito.puede_declarar_entrega
      ? 'Pendiente de entrega'
      : 'No disponible';
  }

  verificarPago(requisito: Requisito): void {
    if (this.admin || this.ocupado()) {
      return;
    }

    const numero =
      this.facturas[
        requisito.id_solicitud_requisito
      ]?.trim();

    if (!numero) {
      this.error.set(
        'Ingresa el número de factura.'
      );
      return;
    }

    if (!this.documentoPago()) {
      this.error.set(
        'No existe un documento de identidad para la verificación.'
      );
      return;
    }

    this.ocupado.set(true);
    this.error.set('');
    this.mensaje.set('');

    this.api
      .factura(
        this.id,
        requisito.id_solicitud_requisito,
        numero
      )
      .pipe(
        switchMap(() =>
          this.api.post<PagoVerificacionResultado>(
            `solicitudes/${this.id}/requisitos/` +
              `${requisito.id_solicitud_requisito}/verificar-pago`
          )
        )
      )
      .subscribe({
        next: resultado => {
          if (resultado.estado === 'verificado') {
            this.mostrarAvisoExito(resultado.mensaje);
          } else {
            this.error.set(resultado.mensaje);
          }

          this.cargar(false);
        },

        error: error => this.informarError(error),
      });
  }

  declararDocumentos(): void {
    if (
      this.admin ||
      this.ocupado() ||
      !this.confirmado
    ) {
      return;
    }

    const requisitos =
      this.requisitosFisicosDeclarables();

    if (!requisitos.length) {
      return;
    }

    this.ocupado.set(true);
    this.error.set('');
    this.mensaje.set('');

    from(requisitos)
      .pipe(
        concatMap(requisito =>
          this.api.post(
            `solicitudes/${this.id}/requisitos/` +
              `${requisito.id_solicitud_requisito}/declaracion-fisica`
          )
        ),
        toArray()
      )
      .subscribe({
        next: () =>
          this.actualizarTrasAccion(
            'Entrega informada. La recepción administrativa está pendiente.'
          ),

        error: error => this.informarError(error),
      });
  }

  // =========================================================
  // MODALES
  // =========================================================

  abrir(
    modal: Exclude<ModalSeguimiento, null>,
    requisito: Requisito | null = null
  ): void {
    if (this.ocupado()) {
      return;
    }

    this.modal = modal;
    this.requisitoFisico = requisito;
    this.confirmado = false;
    this.motivo = '';
    this.error.set('');
    this.mensaje.set('');

    if (modal === 'observacion') {
      this.observacion = this.nuevaObservacion();
      this.canalSubsanacionSeleccionado = '';
      this.canalSubsanacionPersonalizado = '';
      this.cargarUnidadesSubsanacion();
    }

    if (modal === 'confirmar_administrativos') {
      this.administrativosSeleccionados = {};
      this.detalleConfirmacionAdministrativa = '';
    }

    if (modal === 'fisico') {
      this.revisionResultado = 'conforme';
      this.revisionObservacion = '';
      this.documentosSeleccionados = {};
    }

    if (modal === 'resultado') {
      this.detalleResultado = '';
      this.tipoFinalizacion = '';
    }

    if (modal === 'intervencion') {
      this.fechaRevision = this.fechaLocal();

      this.resultadoIntervencion =
        this.solicitud()?.tipo_intervencion === 'firma'
          ? 'firmada'
          : 'conforme';

      this.motivoDesacuerdo = '';
    }
  }

  cerrarModal(): void {
    if (this.ocupado()) {
      return;
    }

    this.modal = null;
    this.confirmado = false;
    this.requisitoFisico = null;
    this.requisitoSeleccionado = null;
    this.documentosSeleccionados = {};
    this.administrativosSeleccionados = {};
    this.error.set('');
  }

  // =========================================================
  // OPERACIONES GENERALES
  // =========================================================

  accion(path: string, datos: unknown = {}): void {
    if (this.ocupado()) {
      return;
    }

    if (
      path === 'avanzar' ||
      path.startsWith('etapas/') ||
      path.includes('/etapas/')
    ) {
      this.error.set(
        'El avance por etapas ya no forma parte del sistema.'
      );
      return;
    }

    this.ocupado.set(true);
    this.error.set('');
    this.mensaje.set('');

    this.api
      .post<{ mensaje?: string }>(
        `${this.admin ? 'admin/' : ''}solicitudes/${this.id}/${path}`,
        datos
      )
      .subscribe({
        next: respuesta =>
          this.actualizarTrasAccion(
            respuesta?.mensaje ||
              'Operación registrada correctamente.'
          ),

        error: error => this.informarError(error),
      });
  }

  iniciarAtencion(): void {
    if (!this.admin) {
      return;
    }

    const estado = this.solicitud()?.estado;

    if (
      !['pendiente_recepcion', 'en_revision'].includes(
        estado || ''
      )
    ) {
      return;
    }

    this.accion('iniciar');
  }

  cancelable(): boolean {
    const solicitud = this.solicitud();

    return (
      !this.admin &&
      !!solicitud &&
      ['borrador', 'pendiente_recepcion'].includes(
        solicitud.estado
      ) &&
      !solicitud.requisitos.some(
        requisito => !!requisito.numero_factura
      )
    );
  }

  crearObservacion(): void {
    if (!this.admin) {
      return;
    }

    if (
      !this.observacion.detalle.trim() ||
      !this.observacion.correccion_requerida.trim()
    ) {
      this.error.set(
        'Completa la observación y la corrección requerida.'
      );
      return;
    }

    this.accion('observaciones', {
      ...this.observacion,
      detalle: this.observacion.detalle.trim(),
      correccion_requerida:
        this.observacion.correccion_requerida.trim(),
      canal_subsanacion: this.canalSubsanacionActual(),
    });
  }

  resolverObservacion(idObservacion: number): void {
    if (!this.admin) {
      return;
    }

    this.accion(
      `observaciones/${idObservacion}/resolver`
    );
  }

  // =========================================================
  // RECEPCIÓN Y REVISIÓN DOCUMENTAL
  // =========================================================

  puedeRevisarDocumentacion(): boolean {
    const estado = this.solicitud()?.estado;

    return (
      this.admin &&
      !this.ocupado() &&
      ['en_revision', 'en_proceso'].includes(estado || '') &&
      this.requisitosFisicos().some(
        requisito => !requisito.presentado
      )
    );
  }

  documentosPendientesRecepcion(): Requisito[] {
    return this.requisitosFisicos().filter(
      requisito => !requisito.presentado
    );
  }

  documentosMarcadosRecepcion(): Requisito[] {
    return this.documentosPendientesRecepcion().filter(
      requisito =>
        this.documentosSeleccionados[
          requisito.id_solicitud_requisito
        ] === true
    );
  }

  cantidadDocumentosMarcados(): number {
    return this.documentosMarcadosRecepcion().length;
  }

  seleccionarTodosDocumentosPendientes(
    seleccionar: boolean
  ): void {
    if (this.ocupado()) {
      return;
    }

    for (
      const requisito of
      this.documentosPendientesRecepcion()
    ) {
      this.documentosSeleccionados[
        requisito.id_solicitud_requisito
      ] = seleccionar;
    }
  }

  abrirRevisionDocumentacion(): void {
    if (!this.puedeRevisarDocumentacion()) {
      return;
    }

    this.abrir('fisico');
  }

  guardarRevisionDocumentacion(): void {
    if (!this.admin || this.ocupado()) {
      return;
    }

    const documentos =
      this.documentosMarcadosRecepcion();

    if (!documentos.length) {
      this.error.set(
        'Selecciona al menos un documento de la lista.'
      );
      return;
    }

    if (
      this.revisionResultado === 'correccion' &&
      !this.revisionObservacion.trim()
    ) {
      this.error.set(
        'Describe la corrección que necesita el solicitante.'
      );
      return;
    }

    this.ocupado.set(true);
    this.error.set('');
    this.mensaje.set('');

    if (this.revisionResultado === 'correccion') {
      this.api
        .post(
          `admin/solicitudes/${this.id}/observaciones`,
          {
            detalle: this.revisionObservacion.trim(),
            correccion_requerida:
              this.revisionObservacion.trim(),
            canal_subsanacion:
              'Presentación física en Kardex',
            id_solicitud_requisito:
              documentos.length === 1
                ? documentos[0].id_solicitud_requisito
                : null,
          }
        )
        .subscribe({
          next: () =>
            this.actualizarTrasAccion(
              'Observación registrada. Los documentos continúan pendientes.'
            ),

          error: error => this.informarError(error),
        });

      return;
    }

    from(documentos)
      .pipe(
        concatMap(requisito =>
          this.api.post(
            `admin/solicitudes/${this.id}/requisitos/` +
              `${requisito.id_solicitud_requisito}/presentacion`
          )
        ),
        toArray()
      )
      .subscribe({
        next: () =>
          this.actualizarTrasAccion(
            'Recepción registrada. Los documentos seleccionados quedaron cumplidos.'
          ),

        error: error => {
          this.informarError(error);
          this.cargar(false);
        },
      });
  }

  puedeContinuarProcesamiento(
    solicitud: Solicitud
  ): boolean {
    return [
      'pendiente_recepcion',
      'en_revision',
    ].includes(solicitud.estado);
  }

  // =========================================================
  // INTERVENCIÓN PRESENCIAL
  // =========================================================

  ultimaIntervencion(): IntervencionPresencial | null {
    const intervenciones = this.intervenciones();

    return intervenciones.length
      ? intervenciones[intervenciones.length - 1]
      : null;
  }

  convocatoriaEnviada(
    idIntervencion: number
  ): boolean {
    return this.notificaciones().some(
      notificacion =>
        notificacion.id_intervencion === idIntervencion &&
        notificacion.tipo === 'convocatoria' &&
        notificacion.estado === 'enviado'
    );
  }

  intervencionCompleta(): boolean {
    const tipo =
      this.solicitud()?.tipo_intervencion || 'ninguna';

    if (tipo === 'ninguna') {
      return true;
    }

    const ultima = this.ultimaIntervencion();

    if (!ultima) {
      return false;
    }

    if (
      !this.convocatoriaEnviada(
        ultima.id_intervencion
      )
    ) {
      return false;
    }

    if (tipo === 'firma') {
      return (
        !!this.resolucion() &&
        ultima.tipo === 'firma' &&
        ultima.estado === 'firmada'
      );
    }

    return (
      ultima.tipo === 'conformidad' &&
      ultima.estado === 'conforme'
    );
  }

  puedeEmitirResolucion(): boolean {
    const solicitud = this.solicitud();

    return (
      this.admin &&
      !!solicitud &&
      solicitud.estado === 'en_proceso' &&
      solicitud.tipo_intervencion === 'firma' &&
      !this.resolucion() &&
      !this.ultimaIntervencion() &&
      this.requisitosCompletos() &&
      this.pendientes() === 0
    );
  }

  emitirResolucion(): void {
    if (
      !this.puedeEmitirResolucion() ||
      !this.confirmado
    ) {
      return;
    }

    this.accion('resolucion/emitir');
  }

  puedeConvocar(): boolean {
    const solicitud = this.solicitud();

    if (
      !this.admin ||
      !solicitud ||
      solicitud.estado !== 'en_proceso' ||
      this.pendientes() > 0
    ) {
      return false;
    }

    if (
      solicitud.tipo_intervencion !== 'firma' &&
      solicitud.tipo_intervencion !== 'conformidad'
    ) {
      return false;
    }

    if (
      solicitud.tipo_intervencion === 'firma' &&
      !this.resolucion()
    ) {
      return false;
    }

    const ultima = this.ultimaIntervencion();

    return (
      !ultima ||
      ultima.estado === 'no_conforme' ||
      ultima.estado === 'anulada'
    );
  }

  convocarIntervencion(): void {
    if (
      !this.puedeConvocar() ||
      !this.confirmado
    ) {
      return;
    }

    this.accion(
      'intervenciones/convocar'
    );
  }

  puedeRegistrarIntervencion(): boolean {
    const ultima = this.ultimaIntervencion();

    return (
      this.admin &&
      this.solicitud()?.estado === 'en_proceso' &&
      ultima?.estado === 'convocada' &&
      this.convocatoriaEnviada(
        ultima.id_intervencion
      )
    );
  }

  registrarIntervencion(): void {
    const ultima = this.ultimaIntervencion();
    const tipo =
      this.solicitud()?.tipo_intervencion;

    if (
      !ultima ||
      !this.puedeRegistrarIntervencion()
    ) {
      return;
    }

    if (!this.fechaRevision) {
      this.error.set(
        'Indica la fecha de revisión.'
      );
      return;
    }

    if (
      tipo === 'firma' &&
      this.resultadoIntervencion !== 'firmada'
    ) {
      this.error.set(
        'Este trámite requiere registrar una firma.'
      );
      return;
    }

    if (
      tipo === 'conformidad' &&
      this.resultadoIntervencion === 'firmada'
    ) {
      this.error.set(
        'Selecciona conforme o no conforme.'
      );
      return;
    }

    if (
      this.resultadoIntervencion === 'no_conforme' &&
      !this.motivoDesacuerdo.trim()
    ) {
      this.error.set(
        'Registra el motivo del desacuerdo.'
      );
      return;
    }

    this.accion(
      `intervenciones/${ultima.id_intervencion}/revision`,
      {
        fecha_revision: this.fechaRevision,
        resultado: this.resultadoIntervencion,
        motivo_desacuerdo:
          this.resultadoIntervencion === 'no_conforme'
            ? this.motivoDesacuerdo.trim()
            : null,
      }
    );
  }

  // =========================================================
  // NOTIFICACIONES INSTITUCIONALES
  // Se conserva la lógica para validar convocatorias.
  // No existe una pestaña ni sección visual de notificaciones.
  // =========================================================

  puedeReenviarNotificacion(
    notificacion: NotificacionSolicitud
  ): boolean {
    return (
      this.admin &&
      notificacion.estado !== 'enviado' &&
      this.solicitud()?.estado === 'en_proceso'
    );
  }

  abrirReenvio(idNotificacion: number): void {
    this.idNotificacionReenvio = idNotificacion;
    this.abrir('reenviar');
  }

  reenviarNotificacion(): void {
    const notificacion =
      this.notificaciones().find(
        item =>
          item.id_notificacion ===
          this.idNotificacionReenvio
      );

    if (
      !notificacion ||
      !this.puedeReenviarNotificacion(notificacion) ||
      !this.confirmado
    ) {
      return;
    }

    this.accion(
      `notificaciones/${notificacion.id_notificacion}/reenviar`
    );
  }

  // =========================================================
  // RESULTADO Y ENTREGA
  // =========================================================

  resultadoDisponible(): boolean {
    const solicitud = this.solicitud();

    return (
      this.admin &&
      !!solicitud &&
      solicitud.estado === 'en_proceso' &&
      this.requisitosCompletos() &&
      this.pendientes() === 0 &&
      this.intervencionCompleta()
    );
  }

  finalizar(): void {
    const solicitud = this.solicitud();

    if (
      !solicitud ||
      !this.resultadoDisponible() ||
      !this.confirmado
    ) {
      return;
    }

    if (
      !solicitud.tipo_finalizacion &&
      !this.tipoFinalizacion
    ) {
      this.error.set(
        'Selecciona la modalidad de finalización.'
      );
      return;
    }

    this.accion('finalizar', {
      detalle:
        this.detalleResultado.trim() || null,
      tipo_finalizacion:
        solicitud.tipo_finalizacion ||
        this.tipoFinalizacion,
    });
  }


  // =========================================================
  // NAVEGACIÓN ADMINISTRATIVA
  // =========================================================

  seleccionarAdminTab(tab: AdminTab): void {
    this.adminTab = tab;
  }

  // =========================================================
  // PROGRESO ADMINISTRATIVO
  // =========================================================

  pasosAdministrativos(
    solicitud: Solicitud
  ): PasoAdmin[] {
    const finalizada =
      solicitud.estado === 'finalizada';

    const atencionIniciada = [
      'en_proceso',
      'lista_para_entrega',
      'finalizada',
    ].includes(solicitud.estado);

    const pasos: PasoAdmin[] = [
      {
        clave: 'solicitud',
        titulo: 'Solicitud enviada',
        detalle: solicitud.fecha_envio
          ? new Date(
              solicitud.fecha_envio
            ).toLocaleDateString('es-BO')
          : 'Registrada',
        estado:
          solicitud.estado === 'borrador'
            ? 'actual'
            : 'completado',
      },
      {
        clave: 'atencion',
        titulo: 'Atención administrativa',
        detalle: atencionIniciada
          ? 'Atención iniciada'
          : 'Pendiente de inicio',
        estado: atencionIniciada
          ? 'completado'
          : 'actual',
      },
    ];

    if (this.requisitosObligatorios().length) {
      pasos.push({
        clave: 'requisitos',
        titulo: 'Verificación de requisitos',
        detalle: this.requisitosCompletos()
          ? 'Completados'
          : `${this.cantidadRequisitosPendientes()} pendientes`,
        estado: this.requisitosCompletos()
          ? 'completado'
          : atencionIniciada
            ? 'actual'
            : 'pendiente',
      });
    }

    if (
      solicitud.tipo_intervencion &&
      solicitud.tipo_intervencion !== 'ninguna'
    ) {
      pasos.push({
        clave: 'intervencion',
        titulo:
          solicitud.tipo_intervencion === 'firma'
            ? 'Firma presencial'
            : 'Conformidad presencial',
        detalle: this.intervencionCompleta()
          ? 'Registrada'
          : this.ultimaIntervencion()?.estado ===
              'convocada'
            ? 'Convocatoria pendiente'
            : 'Pendiente',
        estado: this.intervencionCompleta()
          ? 'completado'
          : atencionIniciada
            ? 'actual'
            : 'pendiente',
      });
    }

    pasos.push({
      clave: 'final',
      titulo:
        solicitud.tipo_finalizacion === 'entrega'
          ? 'Entrega del resultado'
          : 'Finalización',
      detalle: finalizada
        ? 'Completada'
        : solicitud.estado === 'lista_para_entrega'
          ? 'Disponible para recojo'
          : 'Pendiente',
      estado: finalizada
        ? 'completado'
        : solicitud.estado === 'lista_para_entrega'
          ? 'actual'
          : 'pendiente',
    });

    return pasos;
  }

  mensajePasoActual(solicitud: Solicitud): string {
    if (solicitud.estado === 'finalizada') {
      return 'El trámite finalizó correctamente.';
    }

    if (
      solicitud.estado === 'lista_para_entrega'
    ) {
      return (
        'El resultado está listo para recojo. ' +
        'La gestión administrativa ha concluido.'
      );
    }

    if (
      solicitud.estado === 'cancelada' ||
      solicitud.estado === 'rechazada'
    ) {
      return (
        'La solicitud está cerrada. ' +
        'El historial permanece disponible.'
      );
    }

    if (
      solicitud.estado === 'pendiente_recepcion' ||
      solicitud.estado === 'en_revision'
    ) {
      return (
        'La solicitud está pendiente de iniciar ' +
        'atención administrativa.'
      );
    }

    if (this.pendientes() > 0) {
      return (
        'Hay observaciones pendientes de resolución.'
      );
    }

    if (!this.requisitosCompletos()) {
      return (
        'La atención continúa. Existen ' +
        `${this.cantidadRequisitosPendientes()} ` +
        'requisitos obligatorios pendientes.'
      );
    }

    if (!this.intervencionCompleta()) {
      if (
        solicitud.tipo_intervencion === 'firma' &&
        !this.resolucion()
      ) {
        return (
          'Registra la emisión de la resolución ' +
          'antes de convocar.'
        );
      }

      if (
        this.ultimaIntervencion()?.estado ===
        'no_conforme'
      ) {
        return (
          'La revisión no obtuvo conformidad. ' +
          'Se requiere una nueva convocatoria.'
        );
      }

      return (
        'La intervención presencial está pendiente.'
      );
    }

    return (
      'Los controles están completos. ' +
      'Puedes registrar el resultado.'
    );
  }
}
