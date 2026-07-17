import { Component } from '@angular/core';
import { NgFor, KeyValuePipe, NgIf, NgSwitch, NgSwitchCase } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  heroPlusCircle,
  heroFolderOpen,
  heroExclamationCircle,
  heroSparkles
} from '@ng-icons/heroicons/outline';
import { SIDEBAR_MENU } from '../../../core/config/sidebar-menu.config';
import { MenuItem } from '../../models/menu-item.model';

@Component({
  selector: 'app-app-sidebar',
  imports: [NgFor, KeyValuePipe, NgIf, NgSwitch, NgSwitchCase, RouterLink, RouterLinkActive, NgIcon],
  providers: [
    provideIcons({
      heroPlusCircle,
      heroFolderOpen,
      heroExclamationCircle,
      heroSparkles
    })
  ],
  templateUrl: './app-sidebar.html',
  styleUrl: './app-sidebar.scss'
})
export class AppSidebar {
  menuItems: MenuItem[] = SIDEBAR_MENU;

  groupedMenu: Record<string, MenuItem[]> = this.menuItems.reduce(
    (acc, item) => {
      const section = item.section ?? 'GENERAL';
      if (!acc[section]) {
        acc[section] = [];
      }
      acc[section].push(item);
      return acc;
    },
    {} as Record<string, MenuItem[]>
  );
}