import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIf, NgFor } from '@angular/common';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  heroSparkles,
  heroPaperAirplane,
  heroTrash,
  heroChevronDown,
  heroChevronUp
} from '@ng-icons/heroicons/outline';

import { RagService } from '../../services/rag.service';
import { RagQueryResponse } from '../../models/rag.models';
import { ChatMessage } from '../../models/chat-message.model';
import { RagChatComponent } from '../rag-chat/rag-chat';

@Component({
  selector: 'app-rag-home',
  standalone: true,
  imports: [FormsModule, NgIf, NgFor, NgIcon, RagChatComponent],
  providers: [
    provideIcons({
      heroSparkles,
      heroPaperAirplane,
      heroTrash,
      heroChevronDown,
      heroChevronUp
    })
  ],
  templateUrl: './rag-home.html',
  styleUrl: './rag-home.scss'
})
export class RagHome {
  private ragService = inject(RagService);

  question = '';
  sessionId = signal<string | null>(null);

  loading = signal(false);
  errorMessage = signal('');
  messages = signal<ChatMessage[]>([]);

  conversationStarted = computed(() => this.messages().length > 0);

  suggestedQuestions: string[] = [
    '¿Cuántas horas de formación integral debe cumplir un estudiante?',
    '¿Cuántos talleres o cursos debe acreditar?',
    '¿Qué debe hacer un estudiante si postula a una beca o posgrado en el exterior?',
    '¿Qué es la prueba de suficiencia?',
    '¿Cuál es la nota mínima de aprobación en la prueba de suficiencia?',
    '¿Qué modalidades de graduación existen?',
    '¿Puede un estudiante postular por excelencia si tiene inhabilitaciones?'
  ];

  submitQuery(): void {
    const trimmedQuestion = this.question.trim();

    if (!trimmedQuestion || this.loading()) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmedQuestion,
      createdAt: new Date(),
      status: 'done',
      sources: [],
      sourcesExpanded: false
    };

    const assistantLoadingMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: 'Consultando información...',
      createdAt: new Date(),
      status: 'loading',
      sources: [],
      sourcesExpanded: false
    };

    this.messages.update((current) => [
      ...current,
      userMessage,
      assistantLoadingMessage
    ]);

    this.loading.set(true);
    this.errorMessage.set('');
    this.question = '';

    this.ragService.query({
      question: trimmedQuestion,
      session_id: this.sessionId()
    }).subscribe({
      next: (response: RagQueryResponse) => {
        this.sessionId.set(response.session_id);

        const assistantResponse: ChatMessage = {
          id: assistantLoadingMessage.id,
          role: 'assistant',
          content: response.answer ?? 'No se obtuvo respuesta.',
          createdAt: new Date(),
          status: 'done',
          sources: response.sources ?? [],
          sourcesExpanded: false
        };

        this.messages.update((current) =>
          current.map((msg) =>
            msg.id === assistantLoadingMessage.id ? assistantResponse : msg
          )
        );

        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error RAG:', error);

        this.messages.update((current) =>
          current.map((msg) =>
            msg.id === assistantLoadingMessage.id
              ? {
                  ...msg,
                  content: 'Ocurrió un error al consultar el módulo informativo.',
                  status: 'error'
                }
              : msg
          )
        );

        this.errorMessage.set('Ocurrió un error al consultar el módulo informativo.');
        this.loading.set(false);
      }
    });
  }

  useSuggestedQuestion(question: string): void {
    this.question = question;
    this.submitQuery();
  }

  clearConversation(): void {
    this.messages.set([]);
    this.errorMessage.set('');
    this.loading.set(false);
    this.question = '';
    this.sessionId.set(null);
  }

  toggleSources(messageId: string): void {
    this.messages.update((current) =>
      current.map((msg) =>
        msg.id === messageId
          ? { ...msg, sourcesExpanded: !msg.sourcesExpanded }
          : msg
      )
    );
  }

  updateQuestion(value: string): void {
    this.question = value;
  }
}