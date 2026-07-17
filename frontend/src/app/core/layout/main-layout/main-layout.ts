import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AppHeader } from '../../../shared/components/app-header/app-header';
import { AppSidebar } from '../../../shared/components/app-sidebar/app-sidebar';
import { AppFooter } from '../../../shared/components/app-footer/app-footer';

@Component({
  selector: 'app-main-layout',
  imports: [RouterOutlet, AppHeader, AppSidebar, AppFooter],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss'
})
export class MainLayout {}