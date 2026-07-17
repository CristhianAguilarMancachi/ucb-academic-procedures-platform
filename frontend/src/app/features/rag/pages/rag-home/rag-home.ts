import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIf, NgFor } from '@angular/common';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { heroSparkles, heroPaperAirplane } from '@ng-icons/heroicons/outline';
import { RagService } from '../../services/rag.service';
import { RagQueryResponse, RagSource } from '../../models/rag.models';

@Component({
  selector: 'app-rag-home',
  imports: [FormsModule, NgIf, NgFor, NgIcon],
  providers: [
    provideIcons({
      heroSparkles,
      heroPaperAirplane
    })
  ],
  templateUrl: './rag-home.html',
  styleUrl: './rag-home.scss'
})
export class RagHome {
  private ragService = inject(RagService);

  question = '';
  loading = false;
  errorMessage = '';
  answer = '';
  sources: RagSource[] = [];

  suggestedQuestions: string[] = [
    '¿Qué requisitos necesito para una legalización?',
    '¿Cómo solicito un certificado de estudios?',
    '¿Cuáles son los requisitos para una homologación?',
    '¿Cuánto demora la emisión de un certificado?',
    '¿Qué trámites puedo realizar en línea?',
    '¿Qué documentos necesito para titularme?'
  ];

  submitQuery(): void {
    const trimmedQuestion = this.question.trim();

    if (!trimmedQuestion) {
      return;
    }

    this.loading = true;
    this.errorMessage = '';
    this.answer = '';
    this.sources = [];

    this.ragService.query({ question: trimmedQuestion }).subscribe({
      next: (response: RagQueryResponse) => {
        this.answer = response.answer;
        this.sources = response.sources ?? [];
        this.loading = false;
      },
      error: () => {
        this.errorMessage = 'Ocurrió un error al consultar el módulo informativo.';
        this.loading = false;
      }
    });
  }

  useSuggestedQuestion(question: string): void {
    this.question = question;
    this.submitQuery();
  }
}