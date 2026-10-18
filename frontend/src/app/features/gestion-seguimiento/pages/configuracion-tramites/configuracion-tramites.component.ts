
import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin, Observable } from 'rxjs';

import { ModalComponent } from '../../../../shared/components/modal/modal.component';
import {
  GestionSeguimientoService,
  mensajeError,
} from '../../services/gestion-seguimiento.service';

import {
  Campo,
  Condicion,
  Economico,
  Lista,
  RequisitoCatalogo,
  Tramite,
  TipoFinalizacion,
  TipoIntervencion,
} from '../../models/gestion-seguimiento.models';

type VistaConfig = 'listado' | 'editor';
type PestanaConfig = 'general' | 'atencion' | 'requisitos';
type ModalEditor = 'campo' | 'requisito' | 'economico' | null;

@Component({
  selector: 'app-configuracion-tramites',
  standalone: true,
  imports: [CommonModule, FormsModule, ModalComponent],
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

  vista: VistaConfig = 'listado';
  pestana: PestanaConfig = 'general';
  modalEditor: ModalEditor = null;
  tramiteCambioEstado: Tramite | null = null;

  pagina = 1;
  busqueda = '';
  id = 0;

  general = this.nuevoGeneral();
  campo = this.nuevoCampo();
  requisito = this.nuevoRequisito();
  economico = this.nuevoEconomico();

  idCampo = 0;
  idRequisito = 0;
  idEconomico = 0;
  requisitoPago = 0;

  condicionOrigen = '';
  condicionCampo = '';
  condicionValor = '';
  condicionTipo = 'texto';

  opcionesCampo = '';
  economicosDelRequisito: Economico[] = [];

  readonly camposPerfil = [
    { clave: 'codigo_estudiante', nombre: 'Código de estudiante' },
    { clave: 'sede', nombre: 'Sede' },
    { clave: 'carrera_programa', nombre: 'Carrera o programa' },
    { clave: 'nivel_academico', nombre: 'Nivel académico' },
    { clave: 'documento_identidad', nombre: 'Documento de identidad' },
  ];

  readonly tiposCampo = [
    { valor: 'texto', nombre: 'Texto corto' },
    { valor: 'texto_largo', nombre: 'Texto largo' },
    { valor: 'entero', nombre: 'Número entero' },
    { valor: 'decimal', nombre: 'Número decimal' },
    { valor: 'fecha', nombre: 'Fecha' },
    { valor: 'booleano', nombre: 'Sí o no' },
    { valor: 'seleccion', nombre: 'Lista de opciones' },
  ];

  ngOnInit(): void {
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
      tipo_intervencion: 'ninguna' as TipoIntervencion,
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

  nuevoRequisito() {
    return {
      nombre: '',
      descripcion: '',
      orden: 1,
      obligatorio: true,
      activo: true,
      requiere_presentacion_fisica: false,
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

  buscarTramites(): void {
    this.pagina = 1;
    this.cargarLista();
  }

  limpiarBusqueda(): void {
    this.busqueda = '';
    this.pagina = 1;
    this.cargarLista();
  }

  cargarLista(): void {
    this.ocupado.set(true);
    this.error.set('');

    this.api.get<Lista<Tramite>>('admin/tramites', {
      pagina: this.pagina,
      busqueda: this.busqueda,
    }).subscribe({
      next: respuesta => {
        this.lista.set(respuesta.items);
        this.total.set(respuesta.total);
        this.ocupado.set(false);
      },
      error: e => this.fallar(e),
    });
  }

  mover(n: number): void {
    const siguiente = this.pagina + n;

    if (
      siguiente < 1 ||
      (n > 0 && this.pagina * 20 >= this.total()) ||
      this.ocupado()
    ) {
      return;
    }

    this.pagina = siguiente;
    this.cargarLista();
  }

  seleccionar(id: number): void {
    this.abrirTramite(id);
  }

  abrirNuevo(): void {
    this.id = 0;
    this.vista = 'editor';
    this.pestana = 'general';
    this.actual.set(null);
    this.general = this.nuevoGeneral();
    this.cerrarEditores();
    this.error.set('');
    this.mensaje.set('');
  }

  nuevo(): void {
    this.abrirNuevo();
  }

  abrirTramite(idTramite: number): void {
    if (this.ocupado()) return;

    this.ocupado.set(true);
    this.error.set('');
    this.mensaje.set('');
    this.cerrarEditores();

    this.api.get<Tramite>(
      `admin/tramites/${idTramite}`
    ).subscribe({
      next: tramite => {
        this.aplicarSeleccion(tramite);
        this.vista = 'editor';
        this.pestana = 'general';
        this.ocupado.set(false);
      },
      error: e => this.fallar(e),
    });
  }

  volverListado(): void {
    if (this.ocupado()) return;

    this.vista = 'listado';
    this.pestana = 'general';
    this.cerrarEditores();
    this.error.set('');
    this.mensaje.set('');
  }

  cambiarPestana(pestana: PestanaConfig): void {
    if (this.ocupado()) return;
    if (!this.id && pestana === 'requisitos') return;

    this.pestana = pestana;
    this.error.set('');
    this.mensaje.set('');
  }

  private aplicarSeleccion(t: Tramite): void {
    this.id = t.id_tramite;
    this.actual.set(t);

    this.general = {
      nombre: t.nombre,
      descripcion: t.descripcion || '',
      activo: !!t.activo,
      publicado: !!t.publicado,
      permite_solicitudes: !!t.permite_solicitudes,
      tiempo_estimado: t.tiempo_estimado || '',
      canales_atencion: t.canales_atencion || '',
      instrucciones: t.instrucciones || '',
      condiciones: t.condiciones || '',
      tipo_finalizacion: t.tipo_finalizacion || '',
      tipo_intervencion: t.tipo_intervencion || 'ninguna',
    };
  }

  tieneAtencionConfigurada(): boolean {
    const g = this.general;
    return !!(
      g.tiempo_estimado.trim() ||
      g.canales_atencion.trim() ||
      g.instrucciones.trim() ||
      g.condiciones.trim()
    );
  }

  nombreTipoCampo(tipo: string): string {
    return this.tiposCampo.find(
      item => item.valor === tipo
    )?.nombre || tipo;
  }

  requisitosActivos(): number {
    return (this.actual()?.requisitos || [])
      .filter(r => r.activo).length;
  }

  private enviar(
    path: string,
    body: unknown,
    editar: boolean,
    mensajeExito: string,
    cerrarModal = false,
    idSeleccionado = this.id,
  ): void {
    if (this.ocupado()) return;

    this.ocupado.set(true);
    this.error.set('');
    this.mensaje.set('');

    const solicitud: Observable<Tramite> = editar
      ? this.api.patch<Tramite>(path, body)
      : this.api.post<Tramite>(path, body);

    solicitud.subscribe({
      next: resultado => {
        const idTramite =
          idSeleccionado || resultado.id_tramite;

        if (!idTramite) {
          this.error.set(
            'El servidor no devolvió el identificador del trámite.'
          );
          this.ocupado.set(false);
          return;
        }

        forkJoin({
          lista: this.api.get<Lista<Tramite>>(
            'admin/tramites',
            {
              pagina: this.pagina,
              busqueda: this.busqueda,
            }
          ),
          tramite: this.api.get<Tramite>(
            `admin/tramites/${idTramite}`
          ),
        }).subscribe({
          next: ({ lista, tramite }) => {
            this.lista.set(lista.items);
            this.total.set(lista.total);
            this.aplicarSeleccion(tramite);
            this.mensaje.set(mensajeExito);
            this.ocupado.set(false);

            if (cerrarModal) {
              this.cerrarEditores();
            }
          },
          error: e => this.fallar(e),
        });
      },
      error: e => this.fallar(e),
    });
  }

  guardar(
    path: string,
    body: unknown,
    editar: boolean,
    idSeleccionado = this.id,
  ): void {
    this.enviar(
      path,
      body,
      editar,
      'La configuración se guardó correctamente.',
      false,
      idSeleccionado,
    );
  }

  guardarGeneral(): void {
    if (this.general.nombre.trim().length < 3) {
      this.error.set(
        'El nombre debe tener al menos tres caracteres.'
      );
      return;
    }

    if (
      this.actual()?.activo &&
      !this.general.activo &&
      !window.confirm(
        'Desactivar este trámite impedirá nuevas solicitudes y conservará las existentes. ¿Continuar?'
      )
    ) return;

    this.enviar(
      `admin/tramites${this.id ? '/' + this.id : ''}`,
      {
        ...this.general,
        nombre: this.general.nombre.trim(),
        tipo_finalizacion:
          this.general.tipo_finalizacion || null,
      },
      !!this.id,
      this.id
        ? 'Los cambios del trámite se guardaron correctamente.'
        : 'Trámite creado. Ahora puedes configurar sus campos y requisitos.',
    );
  }

  prepararCambioActivo(tramite: Tramite): void {
    if (this.ocupado()) return;
    this.tramiteCambioEstado = tramite;
  }

  cambiarActivo(tramite: Tramite): void {
    this.prepararCambioActivo(tramite);
  }

  confirmarCambioActivo(): void {
    const t = this.tramiteCambioEstado;
    if (!t || this.ocupado()) return;

    this.tramiteCambioEstado = null;

    this.enviar(
      `admin/tramites/${t.id_tramite}`,
      { activo: !t.activo },
      true,
      t.activo
        ? 'El trámite fue desactivado.'
        : 'El trámite fue activado.',
      false,
      t.id_tramite,
    );
  }

  cerrarEditores(): void {
    this.modalEditor = null;
  }

  cerrarModalEditor(): void {
    if (this.ocupado()) return;

    this.modalEditor = null;
    this.error.set('');
  }

  abrirNuevoCampo(): void {
    this.idCampo = 0;
    this.campo = this.nuevoCampo();
    this.campo.orden =
      (this.actual()?.campos.length || 0) + 1;
    this.opcionesCampo = '';
    this.error.set('');
    this.modalEditor = 'campo';
  }

  editarCampo(c: Campo): void {
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

    this.opcionesCampo = (
      c.configuracion?.opciones || []
    ).map(x =>
      typeof x === 'string' ? x : x.valor
    ).join('\n');

    this.error.set('');
    this.modalEditor = 'campo';
  }

  guardarCampo(): void {
    if (!this.campo.clave.trim() ||
        !this.campo.etiqueta.trim()) {
      this.error.set(
        'Completa la clave y la etiqueta del campo.'
      );
      return;
    }

    const opciones = this.opcionesCampo
      .split('\n')
      .map(s => s.trim())
      .filter(Boolean);

    if (
      this.campo.tipo_dato === 'seleccion' &&
      !opciones.length
    ) {
      this.error.set(
        'Introduce al menos una opción para la lista.'
      );
      return;
    }

    this.enviar(
      `admin/tramites/${this.id}/campos${
        this.idCampo ? '/' + this.idCampo : ''
      }`,
      {
        ...this.campo,
        clave: this.campo.clave.trim(),
        etiqueta: this.campo.etiqueta.trim(),
        configuracion:
          this.campo.tipo_dato === 'seleccion'
            ? { opciones }
            : null,
      },
      !!this.idCampo,
      'El campo del formulario se guardó correctamente.',
      true,
    );
  }

  abrirNuevoRequisito(): void {
    this.idRequisito = 0;
    this.requisito = this.nuevoRequisito();
    this.requisito.orden =
      (this.actual()?.requisitos.length || 0) + 1;

    this.condicionOrigen = '';
    this.condicionCampo = '';
    this.condicionValor = '';
    this.condicionTipo = 'texto';
    this.economicosDelRequisito = [];

    this.error.set('');
    this.modalEditor = 'requisito';
  }

  editarRequisito(r: RequisitoCatalogo): void {
    this.idRequisito = r.id_requisito;

    this.requisito = {
      nombre: r.nombre,
      descripcion: r.descripcion || '',
      orden: r.orden,
      obligatorio: r.obligatorio,
      activo: !!r.activo,
      requiere_presentacion_fisica:
        r.requiere_presentacion_fisica,
    };

    this.condicionOrigen =
      r.condicion?.origen || '';

    this.condicionCampo =
      r.condicion?.clave ||
      r.condicion?.campo ||
      '';

    this.condicionValor =
      String(r.condicion?.valor ?? '');

    this.condicionTipo =
      typeof r.condicion?.valor === 'boolean'
        ? 'booleano'
        : typeof r.condicion?.valor === 'number'
          ? 'numero'
          : 'texto';

    this.economicosDelRequisito =
      r.configuraciones_economicas || [];

    this.error.set('');
    this.modalEditor = 'requisito';
  }

  cambiarOrigenCondicion(): void {
    this.condicionCampo = '';
    this.condicionValor = '';
    this.condicionTipo = 'texto';
  }

  guardarRequisito(): void {
    if (!this.requisito.nombre.trim()) {
      this.error.set(
        'Introduce el nombre del requisito.'
      );
      return;
    }

    let condicion: Condicion | null = null;

    if (this.condicionOrigen) {
      if (
        !this.condicionCampo ||
        !this.condicionValor.trim()
      ) {
        this.error.set(
          'Selecciona un campo y el valor de la condición.'
        );
        return;
      }

      const valor =
        this.condicionOrigen === 'perfil_academico' ||
        this.condicionTipo === 'texto'
          ? this.condicionValor
          : this.condicionTipo === 'booleano'
            ? this.condicionValor === 'true'
            : Number(this.condicionValor);

      if (
        typeof valor === 'number' &&
        !Number.isFinite(valor)
      ) {
        this.error.set(
          'El valor indicado debe ser un número válido.'
        );
        return;
      }

      condicion =
        this.condicionOrigen === 'solicitud_dato'
          ? {
              origen: 'solicitud_dato',
              clave: this.condicionCampo,
              operador: 'igual',
              valor,
            }
          : {
              origen: 'perfil_academico',
              campo: this.condicionCampo,
              operador: 'igual',
              valor,
            };
    }

    this.enviar(
      `admin/tramites/${this.id}/requisitos${
        this.idRequisito ? '/' + this.idRequisito : ''
      }`,
      {
        ...this.requisito,
        nombre: this.requisito.nombre.trim(),
        condicion,
      },
      !!this.idRequisito,
      'El requisito se guardó correctamente.',
      true,
    );
  }

  abrirNuevoEconomico(): void {
    if (!this.idRequisito) return;

    this.editarEconomico(this.idRequisito);
    this.error.set('');
    this.modalEditor = 'economico';
  }

  editarEconomico(id: number, e?: Economico): void {
    this.requisitoPago = id;
    this.idEconomico =
      e?.id_requisito_economico || 0;

    this.economico = e
      ? {
          concepto: e.concepto,
          monto: e.monto,
          moneda: e.moneda,
          gestion: e.gestion,
          codigo_concepto_externo:
            e.codigo_concepto_externo || '',
          activo: !!e.activo,
        }
      : this.nuevoEconomico();

    this.error.set('');
    this.modalEditor = 'economico';
  }

  volverARequisito(): void {
    if (this.ocupado()) return;

    const r = this.actual()?.requisitos.find(
      item => item.id_requisito === this.requisitoPago
    );

    if (r) {
      this.editarRequisito(r);
    } else {
      this.modalEditor = null;
    }
  }

  guardarEconomico(): void {
    const monto = Number(this.economico.monto);

    if (!this.economico.concepto.trim() ||
        !Number.isFinite(monto) ||
        monto <= 0) {
      this.error.set(
        'Completa el concepto e introduce un monto mayor que cero.'
      );
      return;
    }

    this.enviar(
      `admin/tramites/${this.id}/requisitos/${
        this.requisitoPago
      }/configuraciones-economicas${
        this.idEconomico ? '/' + this.idEconomico : ''
      }`,
      {
        ...this.economico,
        concepto: this.economico.concepto.trim(),
        monto,
        moneda: this.economico.moneda.trim().toUpperCase(),
      },
      !!this.idEconomico,
      'La configuración económica se guardó correctamente.',
      true,
    );
  }

  private fallar(
    e: Parameters<typeof mensajeError>[0],
  ): void {
    this.error.set(mensajeError(e));
    this.ocupado.set(false);
  }
}
