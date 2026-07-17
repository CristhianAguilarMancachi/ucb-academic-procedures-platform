import { Routes } from '@angular/router';
import { MainLayout } from './core/layout/main-layout/main-layout';
import { RagHome } from './features/rag/pages/rag-home/rag-home';

export const routes: Routes = [
  {
    path: '',
    component: MainLayout,
    children: [
      { path: '', redirectTo: 'informacion', pathMatch: 'full' },
      { path: 'informacion', component: RagHome }
    ]
  }
];