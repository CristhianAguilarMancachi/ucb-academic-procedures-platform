import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RagQueryRequest, RagQueryResponse } from '../models/rag.models';

@Injectable({
  providedIn: 'root'
})
export class RagService {
  private http = inject(HttpClient);

  // La solicitud se realiza al mismo dominio desde el cual se abre el frontend.
  // Nginx redirige /rag/query hacia el backend FastAPI.
  private apiUrl = '/rag/query';

  query(body: RagQueryRequest): Observable<RagQueryResponse> {
    return this.http.post<RagQueryResponse>(this.apiUrl, body);
  }
}