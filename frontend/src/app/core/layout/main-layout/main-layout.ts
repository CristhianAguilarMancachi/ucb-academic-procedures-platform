
import {
  Component,
  afterNextRender,
  DestroyRef,
  ElementRef,
  HostListener,
  Injector,
  OnInit,
  inject,
  signal,
  viewChild,
} from '@angular/core';

import {
  NavigationEnd,
  Router,
  RouterOutlet,
} from '@angular/router';

import { filter } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AppSidebar } from '../../../shared/components/app-sidebar/app-sidebar';
import { AppFooter } from '../../../shared/components/app-footer/app-footer';
import { AuthService } from '../../auth/auth.service';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    RouterOutlet,
    AppSidebar,
    AppFooter,
  ],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss',
})
export class MainLayout implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly injector = inject(Injector);

  readonly menuMovilAbierto = signal(false);
  private readonly navigation = viewChild.required<ElementRef<HTMLElement>>('navigation');
  private readonly menuButton = viewChild.required<ElementRef<HTMLButtonElement>>('menuButton');

  constructor() {
    // Al navegar a otra pantalla, cerrar el menú móvil.
    this.router.events
      .pipe(
        filter(
          (event): event is NavigationEnd =>
            event instanceof NavigationEnd
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        this.cerrarMenuMovil();
      });
  }

  ngOnInit(): void {
    if (!this.authService.sesionInicializada()) {
      this.authService.restaurarSesion().subscribe();
    }
  }

  alternarMenuMovil(): void {
    if (this.menuMovilAbierto()) {
      this.cerrarMenuMovil();
      return;
    }
    this.menuMovilAbierto.set(true);
    afterNextRender(() => {
      if (this.menuMovilAbierto()) {
        this.navigation().nativeElement.querySelector<HTMLButtonElement>('button')?.focus();
      }
    }, { injector: this.injector });
  }

  cerrarMenuMovil(): void {
    const estabaAbierto = this.menuMovilAbierto();
    this.menuMovilAbierto.set(false);
    if (estabaAbierto && window.matchMedia('(max-width: 1050px)').matches) {
      this.menuButton().nativeElement.focus();
    }
  }

  @HostListener('window:resize')
  alCambiarViewport(): void {
    if (!window.matchMedia('(max-width: 1050px)').matches) this.cerrarMenuMovil();
  }

  @HostListener('document:keydown', ['$event'])
  alPresionarTecla(event: KeyboardEvent): void {
    if (!this.menuMovilAbierto()) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      this.cerrarMenuMovil();
    } else if (event.key === 'Tab') {
      const elementos = Array.from(this.navigation().nativeElement.querySelectorAll<HTMLElement>(
        'a[href], button:not(:disabled), [tabindex="0"]',
      )).filter(elemento => elemento.getClientRects().length > 0);
      const primero = elementos[0];
      const ultimo = elementos[elementos.length - 1];
      if (event.shiftKey && document.activeElement === primero) {
        event.preventDefault();
        ultimo?.focus();
      } else if (!event.shiftKey && document.activeElement === ultimo) {
        event.preventDefault();
        primero?.focus();
      }
    }
  }
}
