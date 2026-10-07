import {
  HttpClient,
  HttpErrorResponse,
  HttpParams,
} from '@angular/common/http';

import {
  Injectable,
  inject,
} from '@angular/core';

import {
  Lista,
  Solicitud,
  SolicitudResumen,
  Seguimiento,
  Tramite,
  ValorDato,
} from '../models/gestion-seguimiento.models';


export interface ContactoSolicitud {
  nombre_contacto: string;
  telefono_contacto: string;
  correo_contacto: string;
}


@Injectable({
  providedIn: 'root',
})
export class GestionSeguimientoService {
  private readonly http =
    inject(HttpClient);


  get<T>(
    path: string,
    filtros: Record<
      string,
      string | number | undefined
    > = {},
  ) {
    let params =
      new HttpParams();

    Object.entries(
      filtros,
    ).forEach(
      ([clave, valor]) => {
        if (
          valor !== undefined &&
          valor !== null &&
          valor !== ''
        ) {
          params = params.set(
            clave,
            valor,
          );
        }
      },
    );

    return this.http.get<T>(
      `/api/${path}`,
      {
        params,
      },
    );
  }


  post<T>(
    path: string,
    datos: unknown = {},
  ) {
    return this.http.post<T>(
      `/api/${path}`,
      datos,
    );
  }


  patch<T>(
    path: string,
    datos: unknown,
  ) {
    return this.http.patch<T>(
      `/api/${path}`,
      datos,
    );
  }


  catalogo() {
    return this.get<
      Lista<Tramite>
    >(
      'tramites',
    );
  }


  tramite(
    id: number,
  ) {
    return this.get<Tramite>(
      `tramites/${id}`,
    );
  }


  crear(
    id: number,
  ) {
    return this.post<Solicitud>(
      'solicitudes',
      {
        id_tramite:
          id,
      },
    );
  }


  listar(
    admin: boolean,
    filtros: Record<
      string,
      string | number | undefined
    >,
  ) {
    return this.get<
      Lista<SolicitudResumen>
    >(
      admin
        ? 'admin/solicitudes'
        : 'solicitudes/mias',

      filtros,
    );
  }


  detalle(
    id: number,
    admin = false,
  ) {
    return this.get<Solicitud>(
      `${
        admin
          ? 'admin/'
          : ''
      }solicitudes/${id}`,
    );
  }


  seguimiento(
    id: number,
  ) {
    return this.get<Seguimiento>(
      `solicitudes/${id}/seguimiento`,
    );
  }


  guardar(
    id: number,

    datos: {
      id_campo: number;
      valor: ValorDato;
    }[],

    contacto: ContactoSolicitud,
  ) {
    return this.patch<Solicitud>(
      `solicitudes/${id}`,
      {
        datos,

        nombre_contacto:
          contacto.nombre_contacto,

        telefono_contacto:
          contacto.telefono_contacto,

        correo_contacto:
          contacto.correo_contacto,
      },
    );
  }


  preparacion(
    id: number,
  ) {
    return this.get<Tramite>(
      `solicitudes/${id}/preparacion`,
    );
  }


  enviar(
    id: number,
  ) {
    return this.post<Solicitud>(
      `solicitudes/${id}/enviar`,
      {},
    );
  }


  factura(
    id: number,
    requisito: number,
    numero_factura: string,
  ) {
    return this.http.put<Solicitud>(
      `/api/solicitudes/${id}/requisitos/${requisito}/factura`,

      {
        numero_factura,
      },
    );
  }
}


export function mensajeError(
  error: HttpErrorResponse,
): string {
  if (
    typeof error.error?.detail
    === 'string'
  ) {
    return error.error.detail;
  }

  if (
    Array.isArray(
      error.error?.detail,
    )
  ) {
    return error.error.detail
      .map(
        (item: {
          msg: string;
        }) => item.msg,
      )
      .join('. ');
  }

  return (
    'No fue posible completar la operación. ' +
    'Intenta nuevamente.'
  );
}