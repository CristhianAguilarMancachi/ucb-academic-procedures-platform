import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RagQueryRequest, RagQueryResponse } from '../models/rag.models';

@Injectable({
  providedIn: 'root'
})
export class RagService {
  private http = inject(HttpClient);

  private apiUrl = 'http://localhost:8000/rag/query';

  query(body: RagQueryRequest): Observable<RagQueryResponse> {
    return this.http.post<RagQueryResponse>(this.apiUrl, body);
  }
}