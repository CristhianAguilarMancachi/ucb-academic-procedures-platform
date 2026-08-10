import {
  Component,
  inject,
} from '@angular/core';

import {
  NgFor,
  KeyValuePipe,
  NgIf,
  NgSwitch,
  NgSwitchCase,
} from '@angular/common';

import {
  RouterLink,
  RouterLinkActive,
} from '@angular/router';

import {
  NgIcon,
  provideIcons,
} from '@ng-icons/core';

import {
  heroPlusCircle,
  heroFolderOpen,
  heroExclamationCircle,
  heroSparkles,
} from '@ng-icons/heroicons/outline';

import {
  SIDEBAR_MENU,
} from '../../../core/config/sidebar-menu.config';

import {
  MenuItem,
} from '../../models/menu-item.model';

import {
  AuthService,
} from '../../../core/auth/auth.service';


@Component({
  selector: 'app-app-sidebar',

  imports: [
    NgFor,
    KeyValuePipe,
    NgIf,
    NgSwitch,
    NgSwitchCase,
    RouterLink,
    RouterLinkActive,
    NgIcon,
  ],

  providers: [
    provideIcons({
      heroPlusCircle,
      heroFolderOpen,
      heroExclamationCircle,
      heroSparkles,
    }),
  ],

  templateUrl: './app-sidebar.html',
  styleUrl: './app-sidebar.scss',
})
export class AppSidebar {

  readonly authService =
    inject(AuthService);


  get menuItems(): MenuItem[] {

    return SIDEBAR_MENU.filter(
      item => this.puedeVer(item),
    );
  }


  get groupedMenu(): Record<string, MenuItem[]> {

    return this.menuItems.reduce(
      (acc, item) => {

        const section =
          item.section ?? 'GENERAL';

        if (!acc[section]) {
          acc[section] = [];
        }

        acc[section].push(item);

        return acc;
      },

      {} as Record<string, MenuItem[]>,
    );
  }


  private puedeVer(
    item: MenuItem,
  ): boolean {

    if (
      item.requiresAuth
      && !this.authService.autenticado()
    ) {
      return false;
    }


    if (
      item.roles
      && item.roles.length > 0
      && !this.authService.tieneAlgunoDeLosRoles(
        item.roles,
      )
    ) {
      return false;
    }


    return true;
  }
}