import { MenuItem } from '../../shared/models/menu-item.model';

export const SIDEBAR_MENU: MenuItem[] = [
  {
    label: 'Módulo informativo',
    route: '/informacion',
    section: 'INFORMACIÓN',
    badge: 'IA',
    icon: 'sparkles',
  },

  {
    label: 'Nuevo trámite',
    route: '/tramites/nuevo',
    section: 'TRÁMITES',
    icon: 'plus',
    requiresAuth: true,
    roles: ['solicitante'],
  },

  {
    label: 'Mis trámites',
    route: '/mis-solicitudes',
    section: 'TRÁMITES',
    icon: 'folder',
    requiresAuth: true,
    roles: ['solicitante'],
  },

  {
    label: 'Observaciones',
    route: '/observaciones',
    section: 'TRÁMITES',
    icon: 'alert',
    requiresAuth: true,
    roles: ['solicitante'],
  },

  {
    label: 'Perfil',
    route: '/perfil',
    section: 'CUENTA',
    icon: 'folder',
    requiresAuth: true,
  },

  {
    label: 'Sesiones',
    route: '/sesiones',
    section: 'CUENTA',
    icon: 'folder',
    requiresAuth: true,
  },

  {
    label: 'Cambiar contraseña',
    route: '/cambiar-contrasena',
    section: 'CUENTA',
    icon: 'alert',
    requiresAuth: true,
  },

  {
    label: 'Administración de usuarios',
    route: '/admin/usuarios',
    section: 'ADMINISTRACIÓN',
    icon: 'folder',
    requiresAuth: true,
    roles: ['administrador'],
  },
];