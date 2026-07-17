import { Component } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  heroGlobeAlt,
  heroEnvelope,
  heroPhone
} from '@ng-icons/heroicons/outline';

@Component({
  selector: 'app-app-footer',
  imports: [NgIcon],
  providers: [
    provideIcons({
      heroGlobeAlt,
      heroEnvelope,
      heroPhone
    })
  ],
  templateUrl: './app-footer.html',
  styleUrl: './app-footer.scss'
})
export class AppFooter {}