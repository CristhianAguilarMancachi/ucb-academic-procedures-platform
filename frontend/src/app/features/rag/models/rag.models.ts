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

  /*
   * UUID persistente del mensaje del asistente
   * guardado en PostgreSQL.
   */
  message_id: string;

  question: string;
  standalone_question?: string | null;
  answer: string;
  sources: RagSource[];
}


/* =========================================================
   FEEDBACK
   ========================================================= */

export type RagFeedbackRating =
  -1 | 1;


export interface RagFeedbackRequest {
  session_id: string;
  rating: RagFeedbackRating;
}


export interface RagFeedbackResponse {
  id_feedback: string;
  message_id: string;
  rating: RagFeedbackRating;
  created_at: string;
  updated_at: string;
}


export interface RagFeedbackDeleteResponse {
  message_id: string;
  deleted: boolean;
  message: string;
}