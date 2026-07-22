import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RagQueryRequest {
  question: string;
}

export interface RagQuerySource {
  document: string | null;
  page: number | null;
  article_number: string | null;
  chunk_strategy: string | null;
  section: string | null;
  subsection: string | null;
}

export interface RagQueryResponse {
  question: string;
  answer: string;
  sources: RagQuerySource[];
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private readonly apiUrl = 'http://localhost:8000/rag/query';

  constructor(private http: HttpClient) {}

  askQuestion(question: string): Observable<RagQueryResponse> {
    return this.http.post<RagQueryResponse>(this.apiUrl, { question });
  }
}