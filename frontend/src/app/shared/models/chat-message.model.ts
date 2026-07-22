export interface ChatSource {
  document: string | null;
  page: number | null;
  article_number: string | null;
  chunk_strategy: string | null;
  section: string | null;
  subsection: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: ChatSource[];
  createdAt?: Date;
}