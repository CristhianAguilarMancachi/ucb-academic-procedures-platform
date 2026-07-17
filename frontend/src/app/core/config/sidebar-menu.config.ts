import { MenuItem } from '../../shared/models/menu-item.model';

export const SIDEBAR_MENU: MenuItem[] = [
  { label: 'Nuevo trámite', route: '/tramites/nuevo', section: 'TRÁMITES', icon: 'plus' },
  { label: 'Mis trámites', route: '/mis-solicitudes', section: 'TRÁMITES', icon: 'folder' },
  { label: 'Observaciones', route: '/observaciones', section: 'TRÁMITES', icon: 'alert' },
  { label: 'Módulo informativo', route: '/informacion', section: 'INFORMACIÓN', badge: 'IA', icon: 'sparkles' }
];