import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { AnaliticaResponse, PeriodoAnalitica } from './analitica.models';

@Injectable({ providedIn: 'root' })
export class AnaliticaService {
  private readonly http = inject(HttpClient);

  consultar(periodo: PeriodoAnalitica, idTramite: number | null) {
    let params = new HttpParams().set('periodo', periodo);
    if (idTramite !== null) params = params.set('id_tramite', idTramite);
    return this.http.get<AnaliticaResponse>('/api/admin/analitica', { params });
  }
}
