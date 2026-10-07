import { Component, Input } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  heroUser,
  heroEnvelope,
  heroLockClosed,
  heroLockOpen,
  heroEye,
  heroEyeSlash,
  heroArrowRightOnRectangle,
  heroShieldCheck,
  heroCheck,
  heroPaperAirplane,
  heroArrowLeft,
  heroInformationCircle,
  heroArrowPath,
  heroUserPlus,
  heroExclamationCircle,
} from '@ng-icons/heroicons/outline';

@Component({
  selector: 'app-auth-icon',
  standalone: true,
  imports: [NgIcon],
  providers: [
    provideIcons({
      heroUser,
      heroEnvelope,
      heroLockClosed,
      heroLockOpen,
      heroEye,
      heroEyeSlash,
      heroArrowRightOnRectangle,
      heroShieldCheck,
      heroCheck,
      heroPaperAirplane,
      heroArrowLeft,
      heroInformationCircle,
      heroArrowPath,
      heroUserPlus,
      heroExclamationCircle,
    }),
  ],
  template: '<ng-icon [name]="name" aria-hidden="true" />',
  styles: [':host { display: inline-flex; flex: 0 0 auto; } ng-icon { --ng-icon__size: 1em; }'],
})
export class AuthIconComponent {
  @Input() name = 'heroUser';
}
