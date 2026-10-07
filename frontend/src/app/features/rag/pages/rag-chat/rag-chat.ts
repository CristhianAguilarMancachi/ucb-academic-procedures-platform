import {
  Component,
  EventEmitter,
  Input,
  Output,
  inject,
} from '@angular/core';

import {
  FormsModule,
} from '@angular/forms';

import {
  DatePipe,
  NgFor,
  NgIf,
} from '@angular/common';

import {
  finalize,
} from 'rxjs';

import {
  NgIcon,
  provideIcons,
} from '@ng-icons/core';

import {
  heroDocumentDuplicate,
  heroHandThumbDown,
  heroHandThumbUp,
  heroPaperAirplane,
  heroTrash,
} from '@ng-icons/heroicons/outline';

import {
  ChatMessage,
} from '../../models/chat-message.model';

import {
  RagFeedbackRating,
} from '../../models/rag.models';

import {
  RagService,
} from '../../services/rag.service';


@Component({
  selector:
    'app-rag-chat',

  standalone:
    true,

  imports: [
    FormsModule,
    NgIf,
    NgFor,
    NgIcon,
    DatePipe,
  ],

  providers: [
    provideIcons({
      heroDocumentDuplicate,
      heroHandThumbDown,
      heroHandThumbUp,
      heroPaperAirplane,
      heroTrash,
    }),
  ],

  templateUrl:
    './rag-chat.html',

  styleUrl:
    './rag-chat.scss',
})
export class RagChatComponent {

  private readonly ragService =
    inject(
      RagService,
    );


  @Input()
  messages:
    ChatMessage[] = [];


  @Input()
  question =
    '';


  @Input()
  loading =
    false;


  @Output()
  questionChange =
    new EventEmitter<
      string
    >();


  @Output()
  submit =
    new EventEmitter<
      void
    >();


  @Output()
  clear =
    new EventEmitter<
      void
    >();


  onQuestionChange(
    value:
      string,
  ): void {

    this.questionChange
      .emit(
        value,
      );
  }


  onSubmit():
    void {

    this.submit
      .emit();
  }


  onClear():
    void {

    this.clear
      .emit();
  }


  trackByMessageId(
    index:
      number,

    message:
      ChatMessage,
  ): string {

    return message.id;
  }


  getPrimarySource(
    message:
      ChatMessage,
  ) {

    return (
      message.sources
      &&
      message.sources.length
        > 0
    )
      ? message.sources[0]
      : null;
  }


  /* =======================================================
     VALORAR RESPUESTA
     ======================================================= */

  onFeedback(
    message:
      ChatMessage,

    rating:
      RagFeedbackRating,
  ): void {

    /*
     * Una respuesta local o todavía no persistida
     * no puede valorarse.
     */
    if (
      !message.messageId
      ||
      !message.sessionId
      ||
      message.feedbackLoading
    ) {

      return;
    }


    /*
     * Si el usuario vuelve a pulsar la misma
     * valoración activa, la eliminamos.
     */
    if (
      message.feedbackRating
      ===
      rating
    ) {

      this.removeFeedback(
        message,
      );

      return;
    }


    const previousRating =
      message.feedbackRating
      ?? null;


    message.feedbackLoading =
      true;


    /*
     * Actualización optimista:
     * visualmente responde inmediatamente.
     */
    message.feedbackRating =
      rating;


    this.ragService
      .setFeedback(
        message.messageId,
        message.sessionId,
        rating,
      )
      .pipe(
        finalize(
          () => {

            message.feedbackLoading =
              false;
          },
        ),
      )
      .subscribe({

        next: (
          response,
        ) => {

          message.feedbackRating =
            response.rating;
        },


        error: (
          error,
        ) => {

          /*
           * Si el backend falla restauramos
           * el valor anterior.
           */
          message.feedbackRating =
            previousRating;


          console.error(
            'No fue posible guardar la valoración:',
            error,
          );
        },
      });
  }


  /* =======================================================
     ELIMINAR VALORACIÓN
     ======================================================= */

  private removeFeedback(
    message:
      ChatMessage,
  ): void {

    if (
      !message.messageId
      ||
      !message.sessionId
      ||
      message.feedbackLoading
    ) {

      return;
    }


    const previousRating =
      message.feedbackRating
      ?? null;


    message.feedbackLoading =
      true;


    message.feedbackRating =
      null;


    this.ragService
      .deleteFeedback(
        message.messageId,
        message.sessionId,
      )
      .pipe(
        finalize(
          () => {

            message.feedbackLoading =
              false;
          },
        ),
      )
      .subscribe({

        error: (
          error,
        ) => {

          /*
           * Si falló el DELETE se restaura
           * visualmente la valoración.
           */
          message.feedbackRating =
            previousRating;


          console.error(
            'No fue posible eliminar la valoración:',
            error,
          );
        },
      });
  }


  /* =======================================================
     COPIAR RESPUESTA
     ======================================================= */

  async copyResponse(
    content:
      string,
  ): Promise<void> {

    const text =
      content
        ?.trim();


    if (
      !text
    ) {

      return;
    }


    try {

      await navigator
        .clipboard
        .writeText(
          text,
        );

    } catch (
      error
    ) {

      console.error(
        'No fue posible copiar la respuesta:',
        error,
      );
    }
  }
}