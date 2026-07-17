export interface RagSource {
  document: string;
  page: number | null;
  article_number?: string | null;
  chunk_strategy?: string | null;
}

export interface RagQueryRequest {
  question: string;
  selected_tramite?: string | null;
}

export interface RagQueryResponse {
  question: string;
  answer: string;
  sources: RagSource[];
  selected_tramite?: string | null;
}

export interface RagTramite {
  id: string;
  name: string;
  document_names: string[];
}