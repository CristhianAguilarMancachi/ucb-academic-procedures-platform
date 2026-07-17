import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_CONFIG } from '../../../core/config/api.config';
import { RagQueryRequest, RagQueryResponse, RagTramite } from '../models/rag.models';

@Injectable({
  providedIn: 'root'
})
export class RagService {
  private http = inject(HttpClient);
  private baseUrl = API_CONFIG.baseUrl;

  query(payload: RagQueryRequest): Observable<RagQueryResponse> {
    return this.http.post<RagQueryResponse>(`${this.baseUrl}/rag/query`, payload);
  }

  getTramites(): Observable<RagTramite[]> {
    return this.http.get<RagTramite[]>(`${this.baseUrl}/rag/tramites`);
  }
}