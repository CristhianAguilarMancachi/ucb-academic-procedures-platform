import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { AnaliticaComponent } from './analitica.component';
import { AnaliticaResponse } from './analitica.models';
import { ListaSolicitudesComponent } from '../../gestion-seguimiento/pages/lista-solicitudes/lista-solicitudes.component';
import { GestionSeguimientoService } from '../../gestion-seguimiento/services/gestion-seguimiento.service';

const respuesta = (): AnaliticaResponse => ({
  filtros: { periodo: '30_dias', id_tramite: null },
  desde: '2026-09-15T00:00:00-04:00', hasta: '2026-10-14T14:00:00-04:00',
  zona_horaria: 'America/La_Paz', agrupacion: 'semana',
  indicadores: { solicitudes_recibidas: 0, solicitudes_concluidas: 0, tiempo_mediano_dias: null, consultas_rag: 0 },
  evolucion_solicitudes: [{ periodo: '2026-10-12', recibidas: 0, concluidas: 0 }],
  evolucion_rag: [{ periodo: '2026-10-12', consultas: 0 }],
  top_tramites: [], tramites: [{ id_tramite: 2, nombre: 'Certificado' }],
  clasificacion_rag_disponible: false, limitaciones: [],
});

describe('Analítica funcional', () => {
  beforeEach(() => TestBed.configureTestingModule({
    imports: [AnaliticaComponent],
    providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
  }));

  afterEach(() => TestBed.inject(HttpTestingController).verify());

  function iniciar() {
    const fixture = TestBed.createComponent(AnaliticaComponent);
    fixture.detectChanges();
    const req = TestBed.inject(HttpTestingController).expectOne('/api/admin/analitica?periodo=30_dias');
    return { fixture, req, component: fixture.componentInstance };
  }

  it('muestra loading, ceros y mediana no disponible sin confundirlos', () => {
    const { fixture, req } = iniciar();
    expect(fixture.nativeElement.textContent).toContain('Cargando indicadores');
    req.flush(respuesta());
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('dd').length).toBe(4);
    expect(fixture.nativeElement.textContent).toContain('No disponible');
    expect(fixture.nativeElement.textContent).toContain('No hay consultas persistidas');
    expect(fixture.nativeElement.querySelector('[role="alert"]')).toBeNull();
  });

  it('actualiza filtros por HTTP y evita solicitudes simultáneas', () => {
    const { fixture, req, component } = iniciar();
    req.flush(respuesta());
    component.periodo = '90_dias';
    component.idTramite = 2;
    component.actualizar();
    component.actualizar();
    const consulta = TestBed.inject(HttpTestingController).expectOne('/api/admin/analitica?periodo=90_dias&id_tramite=2');
    expect(component.datos()).toBeNull();
    consulta.flush(respuesta());
    fixture.detectChanges();
    expect(component.cargando()).toBe(false);
  });

  it('error HTTP elimina resultados previos y permite reintentar', () => {
    const { fixture, req, component } = iniciar();
    req.flush({}, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('dl')).toBeNull();
    component.actualizar();
    TestBed.inject(HttpTestingController).expectOne('/api/admin/analitica?periodo=30_dias').flush(respuesta());
    expect(component.error()).toBe('');
  });

  it('Top 5 enlaza a la bandeja real con id_tramite', () => {
    const { fixture, req } = iniciar();
    const datos = respuesta();
    datos.top_tramites = [{ id_tramite: 2, nombre: 'Certificado', cantidad: 3 }];
    req.flush(datos);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('a[href="/admin/solicitudes?id_tramite=2"]')).not.toBeNull();
  });
});

describe('Integración con bandeja administrativa', () => {
  it('consume id_tramite del enlace incluso si no está publicado', () => {
    const listar = vi.fn().mockReturnValue(of({ items: [], total: 0 }));
    TestBed.configureTestingModule({ providers: [
      { provide: GestionSeguimientoService, useValue: { listar, catalogo: () => of({ items: [] }) } },
      { provide: ActivatedRoute, useValue: { snapshot: { data: { admin: true }, queryParamMap: { get: () => '2' } } } },
    ] });
    const component = TestBed.runInInjectionContext(() => new ListaSolicitudesComponent());
    component.ngOnInit();
    expect(listar).toHaveBeenCalledWith(true, expect.objectContaining({ id_tramite: '2' }));
    expect(component.tramitesFiltro()[0].id_tramite).toBe(2);
    component.ngOnDestroy();
  });
});
