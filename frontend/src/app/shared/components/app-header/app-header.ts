import {
  Component,
  inject,
  signal,
} from '@angular/core';

import {
  Router,
  RouterLink,
  RouterLinkActive,
} from '@angular/router';

import {
  NgIcon,
  provideIcons,
} from '@ng-icons/core';

import {
  heroChatBubbleLeftRight,
  heroDocumentText,
  heroCog6Tooth,
  heroUserCircle,
  heroArrowRightOnRectangle,
  heroArrowLeftOnRectangle,
} from '@ng-icons/heroicons/outline';

import {
  AuthService,
} from '../../../core/auth/auth.service';

@Component({
  selector: 'app-app-header',
  imports: [
    RouterLink,
    RouterLinkActive,
    NgIcon,
  ],
  providers: [
    provideIcons({
      heroChatBubbleLeftRight,
      heroDocumentText,
      heroCog6Tooth,
      heroUserCircle,
      heroArrowRightOnRectangle,
      heroArrowLeftOnRectangle,
    }),
  ],
  templateUrl: './app-header.html',
  styleUrl: './app-header.scss',
})
export class AppHeader {

  readonly authService =
    inject(AuthService);

  private readonly router =
    inject(Router);

  readonly cerrandoSesion =
    signal(false);


  esAdministrador(): boolean {
    return this.authService
      .tieneRol('administrador');
  }


  cerrarSesion(): void {

    if (this.cerrandoSesion()) {
      return;
    }

    this.cerrandoSesion.set(true);

    this.authService
      .logout()
      .subscribe({

        next: () => {
          this.cerrandoSesion.set(false);

          this.router.navigate([
            '/login',
          ]);
        },

        error: () => {
          this.cerrandoSesion.set(false);

          this.router.navigate([
            '/login',
          ]);
        },
      });
  }
}