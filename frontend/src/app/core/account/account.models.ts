export type EstadoUsuario =
  | 'pendiente_verificacion'
  | 'activo'
  | 'bloqueado'
  | 'inactivo';


/*
 * Se conserva porque forma parte del contrato actual
 * de usuario_correo.
 *
 * La aplicación trabaja ahora con un solo correo activo
 * por usuario, por lo que Mi perfil no utilizará esta
 * clasificación para mostrar dos correos diferentes.
 */
export type TipoCorreo =
  | 'institucional'
  | 'personal';


export interface CorreoResponse {
  id_usuario_correo: number;

  correo: string;

  tipo: TipoCorreo;

  es_principal: boolean;

  verificado: boolean;

  activo: boolean;

  fecha_verificacion:
    string | null;

  fecha_creacion: string;
}


export interface RolResponse {
  id_rol: number;

  nombre: string;

  descripcion:
    string | null;

  activo: boolean;
}


export interface UsuarioResponse {
  id_usuario: number;

  nombres: string;

  apellidos: string;

  /*
   * Puede ser null en cuentas antiguas o cuando
   * todavía no se registró un teléfono.
   */
  telefono:
    string | null;

  estado:
    EstadoUsuario;

  fecha_ultimo_acceso:
    string | null;

  fecha_creacion:
    string;

  fecha_actualizacion:
    string;
}


export interface UsuarioAutenticadoResponse
  extends UsuarioResponse {

  /*
   * Indica si la cuenta dispone de una contraseña local.
   *
   * No representa ni expone el hash de contraseña.
   *
   * false:
   * la cuenta puede depender únicamente de un proveedor
   * externo, por ejemplo Google.
   *
   * true:
   * la cuenta también permite autenticación local mediante
   * correo y contraseña.
   */
  tiene_contrasena:
    boolean;


  /*
   * Puede contener registros históricos inactivos,
   * pero la base de datos permite solamente un correo
   * activo para la cuenta.
   */
  correos:
    CorreoResponse[];

  roles:
    RolResponse[];
}


export interface UsuarioActualizarRequest {
  nombres?:
    string | null;

  apellidos?:
    string | null;

  /*
   * undefined:
   * no modificar el teléfono.
   *
   * null:
   * eliminar el teléfono actual.
   *
   * string:
   * guardar el nuevo teléfono.
   */
  telefono?:
    string | null;
}