import { Component, input } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';

import {
  heroDocumentText,
  heroChatBubbleLeftRight,
  heroUserCircle,
  heroCog6Tooth,
  heroClock,
  heroTag,
  heroArrowDownTray,
  heroInformationCircle,
  heroChevronDown,
} from '@ng-icons/heroicons/outline';

@Component({
  selector: 'app-gestion-icon',
  standalone: true,

  imports: [NgIcon],

  providers: [
    provideIcons({
      heroDocumentText,
      heroChatBubbleLeftRight,
      heroUserCircle,
      heroCog6Tooth,
      heroClock,
      heroTag,
      heroArrowDownTray,
      heroInformationCircle,
      heroChevronDown,
    }),
  ],

  template: `
    <ng-icon
      [name]="iconos[tipo()]"
      aria-hidden="true"
    />
  `,

  styles: [
    `
      :host {
        display: inline-flex;
        align-items: center;
        justify-content: center;

        vertical-align: middle;

        color: #ffcf13;

        margin-right: 10px;

        font-size: 1.2rem;

        flex-shrink: 0;
      }

      ng-icon {
        display: inline-flex;
      }
    `,
  ],
})
export class IconoGestionComponent {
  readonly tipo = input<
    | 'documento'
    | 'observacion'
    | 'persona'
    | 'proceso'
    | 'reloj'
    | 'precio'
    | 'detalle'
    | 'descripcion'
    | 'chevron'
  >('documento');

  readonly iconos = {
    documento: 'heroDocumentText',
    observacion: 'heroChatBubbleLeftRight',
    persona: 'heroUserCircle',
    proceso: 'heroCog6Tooth',

    reloj: 'heroClock',
    precio: 'heroTag',
    detalle: 'heroArrowDownTray',
    descripcion: 'heroDocumentText',
    chevron: 'heroChevronDown',
  };
}