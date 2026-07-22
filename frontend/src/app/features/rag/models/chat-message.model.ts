import { RagSource } from './rag.models';

export type ChatMessageRole = 'user' | 'assistant' | 'system';
export type ChatMessageStatus = 'loading' | 'done' | 'error';

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  createdAt: Date;
  status: ChatMessageStatus;
  sources?: RagSource[];
  sourcesExpanded?: boolean;
}