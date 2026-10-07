import {
  Injectable,
  inject,
} from '@angular/core';

import {
  HttpClient,
  HttpErrorResponse,
  HttpParams,
} from '@angular/common/http';

import {
  Observable,
} from 'rxjs';

import {
  RagFeedbackDeleteResponse,
  RagFeedbackRating,
  RagFeedbackResponse,
  RagQueryRequest,
  RagQueryResponse,
} from '../models/rag.models';


@Injectable({
  providedIn:
    'root',
})
export class RagService {

  private readonly http =
    inject(
      HttpClient,
    );


  /*
   * Nginx redirige /api hacia FastAPI.
   */
  private readonly apiBase =
    '/api/rag';


  /* =======================================================
     CONSULTA RAG
     ======================================================= */

  query(
    body:
      RagQueryRequest,
  ): Observable<
    RagQueryResponse
  > {

    return this.http
      .post<
        RagQueryResponse
      >(
        `${this.apiBase}/query`,
        body,
      );
  }


  /* =======================================================
     CREAR / ACTUALIZAR VALORACIÓN
     ======================================================= */

  setFeedback(
    messageId:
      string,

    sessionId:
      string,

    rating:
      RagFeedbackRating,
  ): Observable<
    RagFeedbackResponse
  > {

    return this.http
      .put<
        RagFeedbackResponse
      >(
        (
          `${this.apiBase}`
          + `/messages/${messageId}`
          + '/feedback'
        ),
        {
          session_id:
            sessionId,

          rating,
        },
      );
  }


  /* =======================================================
     ELIMINAR VALORACIÓN
     ======================================================= */

  deleteFeedback(
    messageId:
      string,

    sessionId:
      string,
  ): Observable<
    RagFeedbackDeleteResponse
  > {

    const params =
      new HttpParams()
        .set(
          'session_id',
          sessionId,
        );


    return this.http
      .delete<
        RagFeedbackDeleteResponse
      >(
        (
          `${this.apiBase}`
          + `/messages/${messageId}`
          + '/feedback'
        ),
        {
          params,
        },
      );
  }


  /* =======================================================
     MENSAJES DE ERROR
     ======================================================= */

  getUserFriendlyErrorMessage(
    error:
      unknown,
  ): string {

    if (
      !(
        error
        instanceof
        HttpErrorResponse
      )
    ) {

      return (
        'No pude procesar tu consulta en este momento. '
        + 'Intenta nuevamente en unos instantes.'
      );
    }


    /*
     * status = 0 normalmente significa que Angular
     * no logró establecer conexión con el servidor.
     */
    if (
      error.status
      ===
      0
    ) {

      return (
        'No pude conectarme al módulo informativo en este momento. '
        + 'Intenta nuevamente en unos instantes.'
      );
    }


    const backendDetail =
      typeof error.error?.detail
        === 'string'
        ? error.error
            .detail
            .trim()
        : '';


    if (
      error.status
        ===
        400
      ||
      error.status
        ===
        422
    ) {

      return (
        backendDetail
        ||
        (
          'No pude interpretar correctamente la consulta. '
          + 'Intenta reformularla indicando el trámite o tema.'
        )
      );
    }


    if (
      error.status
      ===
      503
    ) {

      return (
        backendDetail
        ||
        (
          'No pude procesar tu consulta en este momento. '
          + 'Intenta nuevamente en unos instantes.'
        )
      );
    }


    if (
      error.status
      >=
      500
    ) {

      return (
        'No pude procesar tu consulta en este momento. '
        + 'Intenta nuevamente en unos instantes.'
      );
    }


    if (
      backendDetail
    ) {

      return backendDetail;
    }


    return (
      'No pude procesar tu consulta en este momento. '
      + 'Intenta nuevamente en unos instantes.'
    );
  }
}