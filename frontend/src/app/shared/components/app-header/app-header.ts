import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  heroChatBubbleLeftRight,
  heroDocumentText,
  heroCog6Tooth
} from '@ng-icons/heroicons/outline';

@Component({
  selector: 'app-app-header',
  imports: [RouterLink, RouterLinkActive, NgIcon],
  providers: [
    provideIcons({
      heroChatBubbleLeftRight,
      heroDocumentText,
      heroCog6Tooth
    })
  ],
  templateUrl: './app-header.html',
  styleUrl: './app-header.scss'
})
export class AppHeader {}