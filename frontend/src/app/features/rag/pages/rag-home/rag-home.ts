import {
  Component,
  computed,
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
} from '../../models/rag.models';

import {
  ChatMessage,
} from '../../models/chat-message.model';

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

  clearConversation():
    void {

    this.messages
      .set(
        [],
      );


    this.errorMessage
      .set(
        '',
      );


    this.loading
      .set(
        false,
      );


    this.question =
      '';


    this.sessionId
      .set(
        null,
      );
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