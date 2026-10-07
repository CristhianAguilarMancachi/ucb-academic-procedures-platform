import {
  RagFeedbackRating,
  RagSource,
} from './rag.models';


export type ChatMessageRole =
  'user'
  | 'assistant'
  | 'system';


export type ChatMessageStatus =
  'loading'
  | 'done'
  | 'error';


export interface ChatMessage {

  /*
   * Identificador local utilizado por Angular
   * para renderizar y actualizar el mensaje.
   */
  id: string;


  /*
   * UUID persistente de chat_message.
   *
   * Solo existe cuando el backend logró guardar
   * realmente esa respuesta.
   */
  messageId?: string | null;


  /*
   * Sesión RAG a la que pertenece la respuesta.
   *
   * Se conserva junto al mensaje para poder
   * realizar su valoración posteriormente.
   */
  sessionId?: string | null;


  role: ChatMessageRole;

  content: string;

  createdAt: Date;

  status: ChatMessageStatus;

  sources?: RagSource[];


  /*
   * Valoración actual:
   *
   *  1 -> Me gusta
   * -1 -> No me gusta
   * null -> Sin valoración
   */
  feedbackRating?:
    RagFeedbackRating | null;


  /*
   * Evita múltiples solicitudes simultáneas
   * mientras se guarda una valoración.
   */
  feedbackLoading?:
    boolean;
}