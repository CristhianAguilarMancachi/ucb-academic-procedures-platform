export interface RagSource {
  document: string | null;
  page: number | null;
  article_number: string | null;
  chunk_strategy: string | null;
  section: string | null;
  subsection: string | null;
}

export interface RagQueryRequest {
  question: string;
  session_id?: string | null;
}

export interface RagQueryResponse {
  session_id: string;
  question: string;
  standalone_question?: string | null;
  answer: string;
  sources: RagSource[];
}