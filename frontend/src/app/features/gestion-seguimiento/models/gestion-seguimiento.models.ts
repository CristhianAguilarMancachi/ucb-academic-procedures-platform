export type EstadoSolicitud =
  | 'borrador'
  | 'pendiente_recepcion'
  | 'en_revision'
  | 'en_proceso'
  | 'lista_para_entrega'
  | 'finalizada'
  | 'cancelada'
  | 'rechazada';


export type TipoFinalizacion =
  | 'entrega'
  | 'resultado_registrado'
  | 'externo';


export type ValorDato =
  | string
  | number
  | boolean;


export interface Condicion {
  origen:
    | 'solicitud_dato'
    | 'perfil_academico';

  clave?: string;

  campo?: string;

  operador: 'igual';

  valor: ValorDato;
}


export interface Economico {
  concepto: string;

  monto:
    | string
    | number;

  moneda: string;

  gestion: number;

  codigo_concepto_externo?:
    | string
    | null;

  id_requisito_economico?:
    number;

  activo?:
    boolean;
}


export interface Campo {
  id_campo: number;

  clave: string;

  etiqueta: string;

  descripcion:
    | string
    | null;

  tipo_dato: string;

  obligatorio: boolean;

  orden: number;

  activo?: boolean;

  configuracion: {
    opciones?: (
      | string
      | {
          valor: string;
          etiqueta?: string;
        }
    )[];
  } | null;
}


export interface RequisitoCatalogo {
  id_requisito: number;

  nombre: string;

  descripcion:
    | string
    | null;

  obligatorio: boolean;

  orden: number;

  es_inicial: boolean;

  es_economico: boolean;

  requiere_presentacion_fisica:
    boolean;

  condicion:
    | Condicion
    | null;

  informacion_economica:
    | Economico
    | null;

  id_etapa?:
    | number
    | null;

  activo?:
    boolean;

  configuraciones_economicas?:
    Economico[];
}


export interface EtapaConfigurada {
  id_etapa: number;

  nombre: string;

  descripcion:
    | string
    | null;

  orden: number;

  id_unidad:
    | number
    | null;

  activo: boolean;

  es_inicial: boolean;

  es_final: boolean;

  visible_solicitante:
    boolean;
}


export interface Tramite {
  id_tramite: number;

  nombre: string;

  descripcion:
    | string
    | null;

  permite_solicitudes:
    boolean;

  activo?: boolean;

  publicado?: boolean;

  tiempo_estimado:
    | string
    | null;

  canales_atencion:
    | string
    | null;

  instrucciones:
    | string
    | null;

  condiciones:
    | string
    | null;

  tipo_finalizacion:
    | TipoFinalizacion
    | null;

  pasos: string[];

  campos: Campo[];

  requisitos:
    RequisitoCatalogo[];

  etapas?:
    EtapaConfigurada[];
}


export interface Dato {
  id_campo: number;

  valor: ValorDato;

  etiqueta_snapshot:
    | string
    | null;

  clave_snapshot:
    | string
    | null;
}


export interface Requisito {
  id_solicitud_requisito:
    number;

  nombre: string;

  descripcion:
    | string
    | null;

  obligatorio: boolean;

  id_solicitud_etapa:
    | number
    | null;

  concepto_economico:
    | string
    | null;

  monto_economico:
    | string
    | number
    | null;

  moneda:
    | string
    | null;

  numero_factura:
    | string
    | null;

  requiere_presentacion_fisica:
    boolean;

  presentado: boolean;

  fecha_presentacion:
    | string
    | null;

  estado_verificacion:
    string;

  detalle_verificacion:
    | string
    | null;

  puede_registrar_factura?:
    boolean;

  puede_declarar_entrega?:
    boolean;

  entrega_declarada?:
    boolean;
}


export interface Historial {
  id_solicitud_etapa?:
    | number
    | null;

  id_solicitud_requisito?:
    | number
    | null;

  id_historial: number;

  evento: string;

  detalle: string;

  fecha_evento: string;

  visible_solicitante?:
    boolean;

  id_usuario_actor?:
    | number
    | null;
}


export interface Observacion {
  id_observacion: number;

  detalle: string;

  correccion_requerida:
    string;

  canal_subsanacion:
    | string
    | null;

  estado: string;

  fecha_observacion:
    string;

  fecha_resolucion:
    | string
    | null;

  id_solicitud_requisito:
    | number
    | null;
}


export interface Etapa {
  id_solicitud_etapa:
    number;

  nombre: string;

  estado: string;

  orden: number;

  fecha_inicio:
    | string
    | null;

  fecha_finalizacion:
    | string
    | null;

  visible_solicitante?:
    boolean;
}


export interface Resultado {
  tipo_finalizacion:
    TipoFinalizacion;

  detalle:
    | string
    | null;

  fecha_registro:
    string;
}


export interface Entrega {
  receptor: string;

  nombre_receptor:
    | string
    | null;

  documento_identidad:
    | string
    | null;

  detalle:
    | string
    | null;

  fecha_entrega:
    string;
}


export interface Pago {
  id_verificacion_pago:
    number;

  id_solicitud_requisito:
    number;

  numero_factura_consultado:
    string;

  estado: string;

  fecha_verificacion:
    string;
}


export interface SolicitudResumen {
  fecha_actualizacion?:
    string;

  id_solicitud:
    number;

  id_tramite:
    number;

  estado:
    EstadoSolicitud;

  fecha_creacion:
    string;

  fecha_envio:
    | string
    | null;

  nombre_tramite_snapshot?:
    | string
    | null;

  nombre_tramite?:
    string;

  tramite?: {
    nombre: string;
  };

  id_solicitante?:
    number;

  /*
   * La bandeja administrativa devuelve
   * estos datos directamente.
   */
  nombre_solicitante?:
    string;

  documento_identidad?:
    | string
    | null;
}


export interface Solicitud
  extends SolicitudResumen
{
  documento_identidad_pago?:
    | string
    | null;

  datos:
    Dato[];

  requisitos:
    Requisito[];

  tipo_finalizacion:
    | TipoFinalizacion
    | null;

  perfil_academico?:
    | Record<
        string,
        string | null
      >
    | null;

  id_etapa_actual?:
    | number
    | null;

  etapas?:
    Etapa[];

  observaciones?:
    Observacion[];

  historial?:
    Historial[];

  resultado?:
    | Resultado
    | null;

  entrega?:
    | Entrega
    | null;

  recepcion?: {
    fecha_recepcion:
      string;

    id_usuario_receptor:
      number;
  } | null;

  pagos?:
    Pago[];
}


export interface Seguimiento {
  nombre_tramite:
    string;

  etapa_actual:
    | Etapa
    | null;

  etapas:
    Etapa[];

  avance_porcentaje:
    number;

  observaciones:
    Observacion[];

  observaciones_pendientes:
    number;

  historial:
    Historial[];

  resultado:
    | Resultado
    | null;

  fecha_entrega:
    | string
    | null;
}


export interface Lista<T> {
  items:
    T[];

  total:
    number;

  pagina?:
    number;
}


/*
 * Se conserva lista_para_entrega por compatibilidad
 * con solicitudes históricas.
 *
 * Ya no debe utilizarse como estado operativo nuevo.
 */
export const ESTADOS:
  EstadoSolicitud[] = [
    'borrador',
    'pendiente_recepcion',
    'en_revision',
    'en_proceso',
    'lista_para_entrega',
    'finalizada',
    'cancelada',
    'rechazada',
  ];


/*
 * Estados que sí se muestran actualmente
 * en los filtros de la interfaz.
 *
 * lista_para_entrega queda fuera porque
 * ya no forma parte del flujo operativo nuevo.
 */
export const ESTADOS_FILTRO:
  EstadoSolicitud[] = [
    'borrador',
    'pendiente_recepcion',
    'en_revision',
    'en_proceso',
    'finalizada',
    'cancelada',
    'rechazada',
  ];


export function etiquetaEstado(
  estado: string,
): string {
  const etiquetas:
    Record<string, string> = {
      borrador:
        'Borrador',

      pendiente_recepcion:
        'Pendiente de recepción',

      en_revision:
        'En revisión',

      en_proceso:
        'En proceso',

      /*
       * Solo para registros históricos.
       */
      lista_para_entrega:
        'Lista para entrega',

      finalizada:
        'Finalizada',

      cancelada:
        'Cancelada',

      rechazada:
        'Rechazada',

      en_curso:
        'En curso',

      completada:
        'Completada',

      pendiente:
        'Pendiente',

      cumple:
        'Cumple',

      no_cumple:
        'No cumple',
    };

  return (
    etiquetas[estado] ||
    estado.replaceAll(
      '_',
      ' ',
    )
  );
}