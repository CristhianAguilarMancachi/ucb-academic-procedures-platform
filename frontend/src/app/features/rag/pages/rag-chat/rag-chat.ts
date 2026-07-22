import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIf, NgFor, DatePipe } from '@angular/common';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  heroPaperAirplane,
  heroTrash,
  heroChevronDown,
  heroChevronUp
} from '@ng-icons/heroicons/outline';

import { ChatMessage } from '../../models/chat-message.model';

@Component({
  selector: 'app-rag-chat',
  standalone: true,
  imports: [FormsModule, NgIf, NgFor, NgIcon, DatePipe],
  providers: [
    provideIcons({
      heroPaperAirplane,
      heroTrash,
      heroChevronDown,
      heroChevronUp
    })
  ],
  templateUrl: './rag-chat.html',
  styleUrl: './rag-chat.scss'
})
export class RagChatComponent {
  @Input() messages: ChatMessage[] = [];
  @Input() question = '';
  @Input() loading = false;

  @Output() questionChange = new EventEmitter<string>();
  @Output() submit = new EventEmitter<void>();
  @Output() clear = new EventEmitter<void>();
  @Output() toggleSources = new EventEmitter<string>();

  onQuestionChange(value: string): void {
    this.questionChange.emit(value);
  }

  onSubmit(): void {
    this.submit.emit();
  }

  onClear(): void {
    this.clear.emit();
  }

  onToggleSources(messageId: string): void {
    this.toggleSources.emit(messageId);
  }

  trackByMessageId(index: number, message: ChatMessage): string {
    return message.id;
  }

  getPrimarySource(message: ChatMessage) {
    return message.sources && message.sources.length > 0 ? message.sources[0] : null;
  }

  getAdditionalSourcesCount(message: ChatMessage): number {
    return message.sources && message.sources.length > 1 ? message.sources.length - 1 : 0;
  }

  getAdditionalSources(message: ChatMessage) {
    return message.sources && message.sources.length > 1 ? message.sources.slice(1) : [];
  }
}