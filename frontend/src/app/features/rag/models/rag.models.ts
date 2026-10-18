export interface RagSource {
  document: string | null;
  page: number | null;
  article_number: string | null;
  chunk_strategy: string | null;
  section: string | null;
  subsection: string | null;
}


export interface RagStoredMessage {
  id_message: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  sources_json: RagSource[] | null;
  feedback_rating: RagFeedbackRating | null;
}

export interface RagCurrentChatResponse {
  session_id: string | null;
  messages: RagStoredMessage[];
}

export interface RagClearChatResponse {
  deleted: boolean;
  message: string;
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
export interface VigenciaDocumento {
  vigente_desde: string;
  vigente_hasta: string | null;
}

export interface DocumentoCrear extends VigenciaDocumento {
  titulo: string;
  unidad_origen: string;
  descripcion: string | null;
  estado: 'activo' | 'inactivo';
}

export interface VersionCrear extends VigenciaDocumento {
  observacion: string | null;
}

export interface VersionDocumento {
  id_version_documento: number;
  numero_version: string;
  estado: string;
  fecha_version: string;
  vigente_desde: string | null;
  vigente_hasta: string | null;
  desde_efectivo: string;
  vigente: boolean;
  cantidad_chunks: number;
  descargable: boolean;
  observacion: string | null;
}

export interface DocumentoInstitucional {
  id_documento_institucional: number;
  titulo: string;
  unidad_origen: string;
  descripcion: string | null;
  estado: string;
  fecha_carga: string;
  fecha_actualizacion: string;
  id_version_actual: number | null;
  version_actual: VersionDocumento | null;
  utilizable_rag: boolean;
}

export interface DocumentoDetalle extends DocumentoInstitucional {
  versiones: VersionDocumento[];
}

export interface ListaDocumentos {
  items: DocumentoInstitucional[];
  total: number;
  pagina: number;
  por_pagina: number;
}
