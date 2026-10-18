export type PeriodoAnalitica = '30_dias' | '90_dias' | '12_meses';

export interface TramiteAnalitica {
  id_tramite: number;
  nombre: string;
}

export interface AnaliticaResponse {
  filtros: { periodo: PeriodoAnalitica; id_tramite: number | null };
  desde: string;
  hasta: string;
  zona_horaria: string;
  agrupacion: 'semana' | 'mes';
  indicadores: {
    solicitudes_recibidas: number;
    solicitudes_concluidas: number | null;
    tiempo_mediano_dias: number | null;
    consultas_rag: number;
  };
  evolucion_solicitudes: { periodo: string; recibidas: number; concluidas: number | null }[];
  top_tramites: (TramiteAnalitica & { cantidad: number })[];
  evolucion_rag: { periodo: string; consultas: number }[];
  tramites: TramiteAnalitica[];
  clasificacion_rag_disponible: boolean;
  limitaciones: string[];
}
