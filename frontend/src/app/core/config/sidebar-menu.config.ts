import {
  MenuItem,
} from '../../shared/models/menu-item.model';


export const SIDEBAR_MENU:
  MenuItem[] = [
  {
    label: 'Analítica e indicadores',
    route: '/admin/analitica',
    section: 'ADMINISTRACIÓN',
    icon: 'chart',
    requiresAuth: true,
    roles: ['personal_administrativo', 'administrador'],
  },
  {
    label: 'Documentos institucionales',
    route: '/admin/documentos',
    section: 'ADMINISTRACIÓN',
    icon: 'document',
    requiresAuth: true,
    roles: ['administrador'],
  },

  {
    label:
      'Módulo informativo',

    route:
      '/informacion',

    section:
      'INFORMACIÓN',

    badge:
      'IA',

    icon:
      'sparkles',
  },

  {
    label:
      'Nuevo trámite',

    route:
      '/tramites',

    section:
      'TRÁMITES',

    icon:
      'plus',

    requiresAuth:
      true,

    roles: [
      'solicitante',
      'administrador',
    ],
  },

  {
    label:
      'Mis trámites',

    route:
      '/mis-solicitudes',

    section:
      'TRÁMITES',

    icon:
      'folder',

    requiresAuth:
      true,

    roles: [
      'solicitante',
      'administrador',
    ],
  },

  {
    label:
      'Gestión de solicitudes',

    route:
      '/admin/solicitudes',

    section:
      'ADMINISTRACIÓN',

    icon:
      'clipboard',

    requiresAuth:
      true,

    roles: [
      'personal_administrativo',
      'administrador',
    ],
  },

  {
    label:
      'Configuración de trámites',

    route:
      '/admin/tramites',

    section:
      'ADMINISTRACIÓN',

    icon:
      'settings',

    requiresAuth:
      true,

    roles: [
      'administrador',
    ],
  },

  {
    label:
      'Administración de usuarios',

    route:
      '/admin/usuarios',

    section:
      'ADMINISTRACIÓN',

    icon:
      'users',

    requiresAuth:
      true,

    roles: [
      'administrador',
    ],
  },
];
