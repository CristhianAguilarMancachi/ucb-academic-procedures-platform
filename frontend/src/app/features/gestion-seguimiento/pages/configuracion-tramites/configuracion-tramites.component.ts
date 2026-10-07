import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { GestionSeguimientoService, mensajeError } from '../../services/gestion-seguimiento.service';
import {
  Campo,
  Condicion,
  Economico,
  EtapaConfigurada,
  Lista,
  RequisitoCatalogo,
  Tramite,
  TipoFinalizacion,
} from '../../models/gestion-seguimiento.models';

@Component({
  selector: 'app-configuracion-tramites',
  standalone: true,
  imports: [CommonModule, FormsModule],
  host: { class: 'm03-view' },
  templateUrl: './configuracion-tramites.component.html',
  styleUrl: './configuracion-tramites.component.scss',
})
export class ConfiguracionTramitesComponent implements OnInit {
  private readonly api = inject(GestionSeguimientoService);
  readonly lista = signal<Tramite[]>([]);
  readonly actual = signal<Tramite | null>(null);
  readonly error = signal('');
  readonly mensaje = signal('');
  readonly ocupado = signal(false);
  readonly total = signal(0);
  pagina = 1;
  busqueda = '';
  id = 0;
  general = this.nuevoGeneral();
  etapa = this.nuevaEtapa();
  requisito = this.nuevoRequisito();
  campo = this.nuevoCampo();
  economico = this.nuevoEconomico();
  idEtapa = 0;
  idRequisito = 0;
  idCampo = 0;
  idEconomico = 0;
  requisitoPago = 0;
  condicionOrigen = '';
  condicionCampo = '';
  condicionValor = '';
  condicionTipo = 'texto';
  readonly camposPerfil = [
    'codigo_estudiante',
    'sede',
    'carrera_programa',
    'nivel_academico',
    'documento_identidad',
  ];
  opcionesCampo = '';
  ngOnInit() {
    this.cargarLista();
  }
  nuevoGeneral() {
    return {
      nombre: '',
      descripcion: '',
      activo: true,
      publicado: false,
      permite_solicitudes: false,
      tiempo_estimado: '',
      canales_atencion: '',
      instrucciones: '',
      condiciones: '',
      tipo_finalizacion: '' as TipoFinalizacion | '',
    };
  }
  nuevaEtapa() {
    return {
      nombre: '',
      descripcion: '',
      orden: 1,
      id_unidad: null as number | null,
      es_inicial: false,
      es_final: false,
      visible_solicitante: false,
      activo: true,
    };
  }
  nuevoRequisito() {
    return {
      nombre: '',
      descripcion: '',
      orden: 1,
      obligatorio: true,
      activo: true,
      id_etapa: null as number | null,
      requiere_presentacion_fisica: false,
    };
  }
  nuevoCampo() {
    return {
      clave: '',
      etiqueta: '',
      descripcion: '',
      tipo_dato: 'texto',
      obligatorio: false,
      orden: 1,
      activo: true,
    };
  }
  nuevoEconomico() {
    return {
      concepto: '',
      monto: '' as string | number,
      moneda: 'BOB',
      gestion: new Date().getFullYear(),
      codigo_concepto_externo: '',
      activo: true,
    };
  }
  cargarLista() {
    this.ocupado.set(true);
    this.error.set('');
    this.api
      .get<Lista<Tramite>>('admin/tramites', { pagina: this.pagina, busqueda: this.busqueda })
      .subscribe({
        next: (r) => {
          this.lista.set(r.items);
          this.total.set(r.total);
          this.ocupado.set(false);
        },
        error: (e) => this.fallar(e),
      });
  }
  seleccionar(id: number) {
    this.ocupado.set(true);
    this.error.set('');
    this.api.get<Tramite>(`admin/tramites/${id}`).subscribe({
      next: (t) => {
        this.aplicarSeleccion(t);
        this.ocupado.set(false);
      },
      error: (e) => this.fallar(e),
    });
  }
  private aplicarSeleccion(t: Tramite) {
    this.id = t.id_tramite;
    this.actual.set(t);
    this.general = {
      nombre: t.nombre,
      descripcion: t.descripcion || '',
      activo: !!t.activo,
      publicado: !!t.publicado,
      permite_solicitudes: t.permite_solicitudes,
      tiempo_estimado: t.tiempo_estimado || '',
      canales_atencion: t.canales_atencion || '',
      instrucciones: t.instrucciones || '',
      condiciones: t.condiciones || '',
      tipo_finalizacion: t.tipo_finalizacion || '',
    };
  }
  nuevo() {
    this.id = 0;
    this.actual.set(null);
    this.general = this.nuevoGeneral();
    this.limpiarEditores();
    this.mensaje.set('');
  }
  limpiarEditores() {
    this.idEtapa = 0;
    this.idRequisito = 0;
    this.idCampo = 0;
    this.idEconomico = 0;
    this.requisitoPago = 0;
    this.etapa = this.nuevaEtapa();
    this.requisito = this.nuevoRequisito();
    this.campo = this.nuevoCampo();
    this.economico = this.nuevoEconomico();
    this.condicionOrigen = '';
    this.condicionCampo = '';
    this.condicionValor = '';
    this.opcionesCampo = '';
  }
  guardar(path: string, body: unknown, editar: boolean) {
    this.ocupado.set(true);
    this.error.set('');
    this.mensaje.set('');
    const request = editar
      ? this.api.patch<Tramite>(path, body)
      : this.api.post<Tramite>(path, body);
    request.subscribe({
      next: (r) => {
        this.mensaje.set('Configuración guardada. Las solicitudes enviadas conservan sus datos.');
        // Conservar el ID creado aunque falle la recarga evita repetir el alta.
        this.id = this.id || r.id_tramite;
        this.limpiarEditores();
        forkJoin({
          lista: this.api.get<Lista<Tramite>>('admin/tramites', {
            pagina: this.pagina,
            busqueda: this.busqueda,
          }),
          tramite: this.api.get<Tramite>(`admin/tramites/${this.id}`),
        }).subscribe({
          next: ({ lista, tramite }) => {
            this.lista.set(lista.items);
            this.total.set(lista.total);
            this.aplicarSeleccion(tramite);
            this.ocupado.set(false);
          },
          error: (e) => this.fallar(e),
        });
      },
      error: (e) => this.fallar(e),
    });
  }
  guardarGeneral() {
    this.guardar(
      `admin/tramites${this.id ? '/' + this.id : ''}`,
      { ...this.general, tipo_finalizacion: this.general.tipo_finalizacion || null },
      !!this.id,
    );
  }
  editarEtapa(e: EtapaConfigurada) {
    this.idEtapa = e.id_etapa;
    this.etapa = {
      nombre: e.nombre,
      descripcion: e.descripcion || '',
      orden: e.orden,
      id_unidad: e.id_unidad,
      es_inicial: e.es_inicial,
      es_final: e.es_final,
      visible_solicitante: e.visible_solicitante,
      activo: e.activo,
    };
  }
  guardarEtapa() {
    this.guardar(
      `admin/tramites/${this.id}/etapas${this.idEtapa ? '/' + this.idEtapa : ''}`,
      this.etapa,
      !!this.idEtapa,
    );
  }
  editarRequisito(r: RequisitoCatalogo) {
    this.idRequisito = r.id_requisito;
    this.requisito = {
      nombre: r.nombre,
      descripcion: r.descripcion || '',
      orden: r.orden,
      obligatorio: r.obligatorio,
      activo: !!r.activo,
      id_etapa: r.id_etapa ?? null,
      requiere_presentacion_fisica: r.requiere_presentacion_fisica,
    };
    this.condicionOrigen = r.condicion?.origen || '';
    this.condicionCampo = r.condicion?.clave || r.condicion?.campo || '';
    this.condicionValor = String(r.condicion?.valor ?? '');
    this.condicionTipo =
      typeof r.condicion?.valor === 'boolean'
        ? 'booleano'
        : typeof r.condicion?.valor === 'number'
          ? 'numero'
          : 'texto';
  }
  guardarRequisito() {
    let condicion: Condicion | null = null;
    if (this.condicionOrigen) {
      if (!this.condicionCampo || !this.condicionValor.trim()) {
        this.error.set('Completa el campo y valor de la condición.');
        return;
      }
      const valor =
        this.condicionOrigen === 'perfil_academico' || this.condicionTipo === 'texto'
          ? this.condicionValor
          : this.condicionTipo === 'booleano'
            ? this.condicionValor === 'true'
            : Number(this.condicionValor);
      if (typeof valor === 'number' && !Number.isFinite(valor)) {
        this.error.set('El valor de la condición debe ser numérico.');
        return;
      }
      condicion =
        this.condicionOrigen === 'solicitud_dato'
          ? { origen: 'solicitud_dato', clave: this.condicionCampo, operador: 'igual', valor }
          : { origen: 'perfil_academico', campo: this.condicionCampo, operador: 'igual', valor };
    }
    this.guardar(
      `admin/tramites/${this.id}/requisitos${this.idRequisito ? '/' + this.idRequisito : ''}`,
      { ...this.requisito, condicion },
      !!this.idRequisito,
    );
  }
  editarCampo(c: Campo) {
    this.idCampo = c.id_campo;
    this.campo = {
      clave: c.clave,
      etiqueta: c.etiqueta,
      descripcion: c.descripcion || '',
      tipo_dato: c.tipo_dato,
      obligatorio: c.obligatorio,
      orden: c.orden,
      activo: !!c.activo,
    };
    this.opcionesCampo = (c.configuracion?.opciones || [])
      .map((x) => (typeof x === 'string' ? x : x.valor))
      .join('\n');
  }
  guardarCampo() {
    this.guardar(
      `admin/tramites/${this.id}/campos${this.idCampo ? '/' + this.idCampo : ''}`,
      {
        ...this.campo,
        configuracion:
          this.campo.tipo_dato === 'seleccion'
            ? {
                opciones: this.opcionesCampo
                  .split('\n')
                  .map((s) => s.trim())
                  .filter(Boolean),
              }
            : null,
      },
      !!this.idCampo,
    );
  }
  editarEconomico(id: number, e?: Economico) {
    this.requisitoPago = id;
    this.idEconomico = e?.id_requisito_economico || 0;
    this.economico = e
      ? {
          concepto: e.concepto,
          monto: e.monto,
          moneda: e.moneda,
          gestion: e.gestion,
          codigo_concepto_externo: e.codigo_concepto_externo || '',
          activo: !!e.activo,
        }
      : this.nuevoEconomico();
  }
  guardarEconomico() {
    this.guardar(
      `admin/tramites/${this.id}/requisitos/${this.requisitoPago}/configuraciones-economicas${this.idEconomico ? '/' + this.idEconomico : ''}`,
      this.economico,
      !!this.idEconomico,
    );
  }
  mover(n: number) {
    this.pagina += n;
    this.cargarLista();
  }
  private fallar(e: Parameters<typeof mensajeError>[0]) {
    this.error.set(mensajeError(e));
    this.ocupado.set(false);
  }
}
