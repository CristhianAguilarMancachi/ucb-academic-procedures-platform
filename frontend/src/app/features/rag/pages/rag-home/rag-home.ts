import {
  Component,
  HostListener,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';

import {
  FormsModule,
} from '@angular/forms';

import {
  NgFor,
  NgIf,
} from '@angular/common';

import {
  NgIcon,
  provideIcons,
} from '@ng-icons/core';

import {
  heroChevronRight,
  heroDocumentText,
  heroInformationCircle,
  heroMagnifyingGlass,
  heroPaperAirplane,
} from '@ng-icons/heroicons/outline';

import {
  RagService,
} from '../../services/rag.service';

import {
  RagQueryResponse,
  RagStoredMessage,
} from '../../models/rag.models';

import {
  ChatMessage,
} from '../../models/chat-message.model';

import { AuthService } from '../../../../core/auth/auth.service';

import {
  RagChatComponent,
} from '../rag-chat/rag-chat';


@Component({
  selector:
    'app-rag-home',

  standalone:
    true,

  imports: [
    FormsModule,
    NgIf,
    NgFor,
    NgIcon,
    RagChatComponent,
  ],

  providers: [
    provideIcons({
      heroChevronRight,
      heroDocumentText,
      heroInformationCircle,
      heroMagnifyingGlass,
      heroPaperAirplane,
    }),
  ],

  templateUrl:
    './rag-home.html',

  styleUrl:
    './rag-home.scss',
})
export class RagHome {

  private readonly ragService =
    inject(
      RagService,
    );


  private readonly authService = inject(AuthService);

  readonly persistentChat = computed(
    () => this.authService.autenticado()
  );

  readonly restoringChat = signal(false);

  private currentIdentity: string | null = null;

  constructor() {
    effect(() => {
      const initialized = this.authService.sesionInicializada();
      const user = this.authService.usuarioActual();

      if (!initialized) {
        return;
      }

      const identity = user
        ? `user:${user.id_usuario}`
        : 'visitor';

      if (this.currentIdentity === identity) {
        return;
      }

      this.currentIdentity = identity;
      this.resetLocalConversation();

      if (user) {
        this.restoreConversation(user.id_usuario);
      }
    });
  }

  private restoreConversation(idUsuario: number): void {
    const identity = `user:${idUsuario}`;
    this.restoringChat.set(true);

    this.ragService.getCurrentSession().subscribe({
      next: response => {
        if (this.currentIdentity !== identity) {
          return;
        }

        this.sessionId.set(response.session_id);
        this.messages.set(
          response.messages.map(
            (item: RagStoredMessage): ChatMessage => ({
              id: item.id_message,
              messageId: item.role === 'assistant'
                ? item.id_message
                : null,
              sessionId: response.session_id,
              role: item.role,
              content: item.content,
              createdAt: new Date(item.created_at),
              status: 'done',
              sources: item.sources_json ?? [],
              feedbackRating: item.feedback_rating,
              feedbackLoading: false,
            })
          )
        );
        this.restoringChat.set(false);
      },
      error: error => {
        if (this.currentIdentity !== identity) {
          return;
        }
        console.error('No se pudo recuperar el chat:', error);
        this.errorMessage.set(
          'No se pudo recuperar tu conversación. Intenta recargar la página.'
        );
        this.restoringChat.set(false);
      },
    });
  }

  private resetLocalConversation(): void {
    this.clearModalOpen.set(false);
    this.clearError.set('');
    this.clearingChat.set(false);
    this.messages.set([]);
    this.sessionId.set(null);
    this.question = '';
    this.errorMessage.set('');
    this.loading.set(false);
  }

  question =
    '';


  sessionId =
    signal<
      string | null
    >(
      null,
    );


  loading =
    signal(
      false,
    );


  errorMessage =
    signal(
      '',
    );


  messages =
    signal<
      ChatMessage[]
    >(
      [],
    );


  conversationStarted =
    computed(
      () =>
        this.messages()
          .length
        > 0,
    );


  suggestedQuestions:
    string[] = [

    '¿Cuántas horas de formación integral debe cumplir un estudiante?',

    '¿Cuántos talleres o cursos debe acreditar?',

    '¿Qué debe hacer un estudiante si postula a una beca o posgrado en el exterior?',

    '¿Qué es la prueba de suficiencia?',

    '¿Cuál es la nota mínima de aprobación en la prueba de suficiencia?',

    '¿Qué modalidades de graduación existen?',

    '¿Puede un estudiante postular por excelencia si tiene inhabilitaciones?',
  ];


  /* =======================================================
     ENVIAR CONSULTA
     ======================================================= */

  submitQuery():
    void {

    const trimmedQuestion =
      this.question
        .trim();


    if (
      !trimmedQuestion
      ||
      this.loading()
      || this.restoringChat()
    ) {

      return;
    }


    const userMessage:
      ChatMessage = {

      id:
        crypto.randomUUID(),

      role:
        'user',

      content:
        trimmedQuestion,

      createdAt:
        new Date(),

      status:
        'done',
    };


    /*
     * Mensaje temporal mientras responde
     * el backend.
     */
    const assistantLoadingMessage:
      ChatMessage = {

      id:
        crypto.randomUUID(),

      messageId:
        null,

      sessionId:
        this.sessionId(),

      role:
        'assistant',

      content:
        'Consultando información...',

      createdAt:
        new Date(),

      status:
        'loading',

      sources:
        [],

      feedbackRating:
        null,

      feedbackLoading:
        false,
    };


    this.messages
      .update(
        current => [
          ...current,
          userMessage,
          assistantLoadingMessage,
        ],
      );


    this.loading
      .set(
        true,
      );


    this.errorMessage
      .set(
        '',
      );


    this.question =
      '';


    const requestIdentity = this.currentIdentity;

    this.ragService
      .query({
        question:
          trimmedQuestion,

        session_id:
          this.sessionId(),
      })
      .subscribe({

        next: (
          response:
            RagQueryResponse,
        ) => {
          if (requestIdentity !== this.currentIdentity) {
            return;
          }

          this.sessionId
            .set(
              response
                .session_id,
            );


          const answer =
            response.answer
              ?.trim()
            ||
            (
              'No encontré información suficiente '
              + 'para responder esa consulta.'
            );


          const assistantResponse:
            ChatMessage = {

            /*
             * Conservamos el id local para que Angular
             * sustituya exactamente el loading actual.
             */
            id:
              assistantLoadingMessage
                .id,

            /*
             * Este sí es el UUID persistente
             * guardado en PostgreSQL.
             */
            messageId:
              response
                .message_id,

            sessionId:
              response
                .session_id,

            role:
              'assistant',

            content:
              answer,

            createdAt:
              new Date(),

            status:
              'done',

            sources:
              response.sources
              ?? [],

            feedbackRating:
              null,

            feedbackLoading:
              false,
          };


          this.messages
            .update(
              current =>
                current.map(
                  message =>
                    message.id
                    ===
                    assistantLoadingMessage.id
                      ? assistantResponse
                      : message,
                ),
            );


          this.loading
            .set(
              false,
            );
        },


        error: (
          error:
            unknown,
        ) => {
          if (requestIdentity !== this.currentIdentity) {
            return;
          }

          console.error(
            'Error técnico del módulo RAG:',
            error,
          );


          const friendlyMessage =
            this.ragService
              .getUserFriendlyErrorMessage(
                error,
              );


          this.messages
            .update(
              current =>
                current.map(
                  message =>
                    message.id
                    ===
                    assistantLoadingMessage.id
                      ? {
                          ...message,

                          /*
                           * No posee messageId porque
                           * esta respuesta solo existe
                           * localmente.
                           */
                          messageId:
                            null,

                          content:
                            friendlyMessage,

                          status:
                            'done',

                          sources:
                            [],

                          feedbackRating:
                            null,

                          feedbackLoading:
                            false,
                        }
                      : message,
                ),
            );


          this.errorMessage
            .set(
              '',
            );


          this.loading
            .set(
              false,
            );
        },
      });
  }


  /* =======================================================
     PREGUNTA SUGERIDA
     ======================================================= */

  useSuggestedQuestion(
    question:
      string,
  ): void {

    this.question =
      question;

    this.submitQuery();
  }


  /* =======================================================
     NUEVA CONVERSACIÓN
     ======================================================= */

  readonly clearModalOpen = signal(false);
  readonly clearingChat = signal(false);
  readonly clearError = signal('');

  clearConversation(): void {
    if (
      this.loading() ||
      this.restoringChat() ||
      this.clearingChat()
    ) {
      return;
    }

    this.clearError.set('');
    this.clearModalOpen.set(true);
  }

  cancelClearConversation(): void {
    if (this.clearingChat()) {
      return;
    }

    this.clearModalOpen.set(false);
    this.clearError.set('');
  }

  @HostListener('document:keydown.escape')
  onClearModalEscape(): void {
    if (this.clearModalOpen()) {
      this.cancelClearConversation();
    }
  }

  confirmClearConversation(): void {
    if (
      !this.clearModalOpen() ||
      this.loading() ||
      this.restoringChat() ||
      this.clearingChat()
    ) {
      return;
    }

    const identity = this.currentIdentity;

    this.clearError.set('');
    this.clearingChat.set(true);
    this.loading.set(true);

    this.ragService.clearCurrentSession().subscribe({
      next: () => {
        if (identity !== this.currentIdentity) {
          return;
        }

        this.clearModalOpen.set(false);
        this.clearingChat.set(false);
        this.resetLocalConversation();
      },
      error: error => {
        if (identity !== this.currentIdentity) {
          return;
        }

        console.error('No se pudo limpiar el chat:', error);
        this.clearError.set(
          'No se pudo limpiar el historial. Intenta nuevamente.'
        );
        this.clearingChat.set(false);
        this.loading.set(false);
      },
    });
  }


  /* =======================================================
     ACTUALIZAR INPUT
     ======================================================= */

  updateQuestion(
    value:
      string,
  ): void {

    this.question =
      value;
  }
}