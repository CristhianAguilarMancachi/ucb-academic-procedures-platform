import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ModalComponent } from '../../../../shared/components/modal/modal.component';
import { GestionSeguimientoService, mensajeError } from '../../../gestion-seguimiento/services/gestion-seguimiento.service';
import { Lista, Unidad } from '../../../gestion-seguimiento/models/gestion-seguimiento.models';
import { RagService } from '../../services/rag.service';
import { DocumentoCrear, DocumentoDetalle, DocumentoInstitucional, VersionDocumento } from '../../models/rag.models';

@Component({
  selector: 'app-documentos-institucionales',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, ModalComponent],
  templateUrl: './documentos-institucionales.component.html',
  styleUrl: './documentos-institucionales.component.scss',
})
export class DocumentosInstitucionalesComponent implements OnInit {
  private readonly api = inject(RagService);
  private readonly gestion = inject(GestionSeguimientoService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  readonly documentos = signal<DocumentoInstitucional[]>([]);
  readonly detalle = signal<DocumentoDetalle | null>(null);
  readonly unidades = signal<Unidad[]>([]);
  readonly cargando = signal(false);
  readonly ocupado = signal(false);
  readonly error = signal('');
  readonly mensaje = signal('');
  readonly modal = signal<'carga' | 'version' | 'vigencia' | null>(null);

  readonly confirmacion = signal<{
    tipo: 'activar' | 'desactivar' | 'reingestar';
    idDocumento: number;
    tituloDocumento: string;
    idVersion?: number;
    numeroVersion?: string | number;
  } | null>(null);
  readonly total = signal(0);
  pagina = 1;
  idDocumento: number | null = null;
  idVersion = 0;
  archivo: File | null = null;
  formulario = this.nuevoFormulario();
  comentario = '';

  ngOnInit() {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(params => {
      const valor = params.get('id');
      this.idDocumento = valor === null ? null : Number(valor);
      this.detalle.set(null);
      this.cargar();
    });
    this.cargarUnidades();
  }

  private fechaLocalActual(): string {
    const hoy = new Date();
    const anio = hoy.getFullYear();
    const mes = String(hoy.getMonth() + 1).padStart(2, '0');
    const dia = String(hoy.getDate()).padStart(2, '0');
    return `${anio}-${mes}-${dia}`;
  }

  get fechaMaxima(): string {
    return this.fechaLocalActual();
  }

  private nuevoFormulario(): DocumentoCrear {
    return {
      titulo: '',
      unidad_origen: '',
      descripcion: '',
      estado: 'activo',
      vigente_desde: this.fechaLocalActual(),
      vigente_hasta: null,
    };
  }

  cargar() {
    this.error.set('');
    this.cargando.set(true);
    if (this.idDocumento !== null) {
      if (!Number.isSafeInteger(this.idDocumento) || this.idDocumento <= 0) {
        this.error.set('El identificador del documento no es válido.');
        this.cargando.set(false);
        return;
      }
      this.api.documento(this.idDocumento).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: d => { this.detalle.set(d); this.cargando.set(false); },
        error: e => this.fallar(e),
      });
    } else {
      this.api.documentos(this.pagina).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: r => { this.documentos.set(r.items); this.total.set(r.total); this.cargando.set(false); },
        error: e => this.fallar(e),
      });
    }
  }

  private cargarUnidades(pagina = 1) {
    this.gestion.get<Lista<Unidad>>('admin/unidades', { pagina, por_pagina: 100, activo: 'true' })
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: r => {
          this.unidades.update(us => [...us, ...r.items]);
          if (pagina * 100 < r.total) this.cargarUnidades(pagina + 1);
        },
        error: () => this.error.set('No se pudieron cargar las unidades. Recarga la página antes de cargar un documento.'),
      });
  }

  cambiarPagina(delta: number) {
    if (this.cargando() || this.pagina + delta < 1 || (this.pagina + delta - 1) * 20 >= this.total()) return;
    this.pagina += delta;
    this.cargar();
  }

  abrir(tipo: 'carga' | 'version' | 'vigencia', version?: VersionDocumento) {
    this.error.set('');
    this.mensaje.set('');
    this.formulario = this.nuevoFormulario();
    this.archivo = null;
    this.comentario = '';
    this.idVersion = version?.id_version_documento || 0;
    if (version) {
      this.formulario.vigente_desde = version.desde_efectivo;
    }
    this.modal.set(tipo);
  }

  seleccionarArchivo(event: Event) {
    const input = event.target as HTMLInputElement;
    const seleccionado = input.files?.[0] ?? null;

    if (!seleccionado) return;

    this.error.set('');

    if (
      !seleccionado.name.toLowerCase().endsWith('.pdf') ||
      seleccionado.size === 0 ||
      seleccionado.size > 19 * 1024 * 1024
    ) {
      this.error.set('Selecciona un PDF no vacío de hasta 19 MiB.');
      input.value = '';
      return;
    }

    this.archivo = seleccionado;
  }

  quitarArchivo(input: HTMLInputElement) {
    if (this.ocupado()) return;
    this.archivo = null;
    input.value = '';
    this.error.set('');
  }

  tamanoArchivo(bytes: number): string {
    const mb = bytes / (1024 * 1024);
    return `${mb.toLocaleString('es-BO', {
      maximumFractionDigits: 2,
    })} MiB`;
  }

  guardar() {
    if (this.ocupado()) return;
    const vigencia = { vigente_desde: this.formulario.vigente_desde, vigente_hasta: null };
    if (!vigencia.vigente_desde) {
      this.error.set('Indica la fecha de inicio de uso.');
      return;
    }
    if (this.modal() === 'vigencia' && this.idDocumento) {
      this.ejecutar(this.api.vigenciaDocumento(this.idDocumento, this.idVersion, vigencia));
    } else if (!this.archivo) {
      this.error.set('Selecciona un PDF.');
    } else if (this.modal() === 'version' && this.idDocumento) {
      this.ejecutar(this.api.nuevaVersion(this.idDocumento, { ...vigencia, observacion: this.comentario.trim() || null }, this.archivo));
    } else if (this.modal() === 'carga') {
      if (this.formulario.titulo.trim().length < 3 || !this.unidades().some(u => u.nombre === this.formulario.unidad_origen)) {
        this.error.set('Indica un título y selecciona una unidad existente.');
        return;
      }
      this.ejecutar(this.api.cargarDocumento({ ...this.formulario, ...vigencia, titulo: this.formulario.titulo.trim() }, this.archivo));
    }
  }

  cambiarEstado() {
    const d = this.detalle();

    if (!d || this.ocupado() || this.confirmacion()) return;

    this.error.set('');

    this.confirmacion.set({
      tipo: d.estado === 'activo' ? 'desactivar' : 'activar',
      idDocumento: d.id_documento_institucional,
      tituloDocumento: d.titulo,
    });
  }

  reingestar(version: VersionDocumento) {
    const d = this.detalle();

    if (
      !d ||
      this.ocupado() ||
      this.confirmacion() ||
      !version.descargable
    ) {
      return;
    }

    this.error.set('');

    this.confirmacion.set({
      tipo: 'reingestar',
      idDocumento: d.id_documento_institucional,
      tituloDocumento: d.titulo,
      idVersion: version.id_version_documento,
      numeroVersion: version.numero_version,
    });
  }

  cerrarConfirmacion() {
    if (this.ocupado()) return;

    this.confirmacion.set(null);
    this.error.set('');
  }

  confirmarAccion() {
    const accion = this.confirmacion();
    const d = this.detalle();

    if (!accion || !d || this.ocupado()) return;

    if (accion.idDocumento !== d.id_documento_institucional) {
      this.cerrarConfirmacion();
      return;
    }

    if (accion.tipo === 'activar' || accion.tipo === 'desactivar') {
      const estadoEsperado = accion.tipo === 'activar'
        ? 'inactivo'
        : 'activo';

      if (d.estado !== estadoEsperado) {
        this.cerrarConfirmacion();
        return;
      }

      const nuevoEstado = accion.tipo === 'activar'
        ? 'activo'
        : 'inactivo';

      this.ejecutar(
        this.api.estadoDocumento(
          accion.idDocumento,
          nuevoEstado
        )
      );

      return;
    }

    if (accion.tipo === 'reingestar' && accion.idVersion) {
      const version = d.versiones.find(
        v => v.id_version_documento === accion.idVersion
      );

      if (!version?.descargable) {
        this.cerrarConfirmacion();
        return;
      }

      this.ejecutar(
        this.api.reingestarDocumento(
          accion.idDocumento,
          accion.idVersion
        )
      );
    }
  }

  descargar(version: VersionDocumento) {
    if (!this.idDocumento || !version.descargable || this.ocupado()) return;
    this.ocupado.set(true);
    this.error.set('');
    this.api.descargarDocumento(this.idDocumento, version.id_version_documento)
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: blob => {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `documento-${this.idDocumento}-v${version.id_version_documento}.pdf`;
          link.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
          this.ocupado.set(false);
        },
        error: e => this.fallar(e),
      });
  }

  private ejecutar(request: Observable<DocumentoDetalle>) {
    this.ocupado.set(true);
    this.error.set('');
    this.mensaje.set('');
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: d => {
        this.detalle.set(d);
        this.modal.set(null);
        this.confirmacion.set(null);
        this.ocupado.set(false);
        this.mensaje.set('Operación completada.');
        if (this.idDocumento !== d.id_documento_institucional) {
          void this.router.navigate(['/admin/documentos', d.id_documento_institucional]);
        }
      },
      error: e => this.fallar(e),
    });
  }

  private fallar(error: HttpErrorResponse) {
    this.error.set(mensajeError(error));
    this.cargando.set(false);
    this.ocupado.set(false);
  }
}
