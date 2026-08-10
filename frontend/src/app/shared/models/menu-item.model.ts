export interface MenuItem {

  label: string;

  route: string;

  icon?: string;

  badge?: string;

  section?: string;

  requiresAuth?: boolean;

  roles?: string[];
}