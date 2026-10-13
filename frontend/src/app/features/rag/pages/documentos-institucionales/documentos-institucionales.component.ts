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

  private nuevoFormulario(): DocumentoCrear {
    return { titulo: '', unidad_origen: '', descripcion: '', estado: 'activo', vigente_desde: '', vigente_hasta: null };
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
      this.formulario.vigente_hasta = version.vigente_hasta;
    }
    this.modal.set(tipo);
  }

  seleccionarArchivo(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] || null;
    this.archivo = null;
    this.error.set('');
    if (file && (!file.name.toLowerCase().endsWith('.pdf') || !file.size || file.size > 19 * 1024 * 1024)) {
      this.error.set('Selecciona un PDF no vacío de hasta 19 MiB.');
      input.value = '';
      return;
    }
    this.archivo = file;
  }

  guardar() {
    if (this.ocupado()) return;
    const vigencia = { vigente_desde: this.formulario.vigente_desde, vigente_hasta: this.formulario.vigente_hasta || null };
    if (!vigencia.vigente_desde || (vigencia.vigente_hasta && vigencia.vigente_hasta < vigencia.vigente_desde)) {
      this.error.set('Revisa el período de vigencia.');
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
    if (!d || this.ocupado()) return;
    const estado = d.estado === 'activo' ? 'inactivo' : 'activo';
    if (!window.confirm(`${estado === 'inactivo' ? 'Desactivar' : 'Activar'} «${d.titulo}»? Al desactivar dejará de utilizarse en nuevas respuestas RAG. El PDF, las versiones y el historial se conservarán.`)) return;
    this.ejecutar(this.api.estadoDocumento(d.id_documento_institucional, estado));
  }

  reingestar(version: VersionDocumento) {
    const d = this.detalle();
    if (!d || this.ocupado() || !version.descargable) return;
    if (!window.confirm(`Reingestar «${d.titulo}», versión ${version.numero_version}? Se regenerarán únicamente sus fragmentos y embeddings. Las demás versiones se conservarán.`)) return;
    this.ejecutar(this.api.reingestarDocumento(d.id_documento_institucional, version.id_version_documento));
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
