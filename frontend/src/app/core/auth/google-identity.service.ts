import {
  Injectable,
  inject,
} from '@angular/core';

import {
  HttpClient,
} from '@angular/common/http';

import {
  firstValueFrom,
} from 'rxjs';


interface GoogleConfigResponse {
  client_id: string;
}


interface GoogleCredentialResponse {
  credential?: string;
}


interface GoogleAccountsId {
  initialize(config: {
    client_id: string;
    callback: (
      response: GoogleCredentialResponse,
    ) => void;
  }): void;

  renderButton(
    parent: HTMLElement,
    options: {
      type?: 'standard' | 'icon';
      theme?:
        | 'outline'
        | 'filled_blue'
        | 'filled_black';
      size?:
        | 'large'
        | 'medium'
        | 'small';
      text?:
        | 'signin_with'
        | 'signup_with'
        | 'continue_with'
        | 'signin';
      shape?:
        | 'rectangular'
        | 'pill'
        | 'circle'
        | 'square';
      logo_alignment?:
        | 'left'
        | 'center';
      width?: number;
    },
  ): void;
}


interface GoogleIdentityApi {
  accounts: {
    id: GoogleAccountsId;
  };
}


type WindowGoogle = Window & {
  google?: GoogleIdentityApi;
};


@Injectable({
  providedIn: 'root',
})
export class GoogleIdentityService {

  private readonly http =
    inject(HttpClient);

  private readonly configUrl =
    '/api/auth/google/config';

  private readonly scriptId =
    'google-identity-services';

  private readonly scriptUrl =
    'https://accounts.google.com/gsi/client';

  private clientId: string | null =
    null;


  // =========================================================
  // CLIENT ID
  // =========================================================

  private async obtenerClientId():
    Promise<string> {

    if (this.clientId) {
      return this.clientId;
    }

    const respuesta =
      await firstValueFrom(
        this.http.get<GoogleConfigResponse>(
          this.configUrl,
        ),
      );

    const clientId =
      respuesta.client_id?.trim();

    if (!clientId) {
      throw new Error(
        'Google no está configurado correctamente.',
      );
    }

    this.clientId = clientId;

    return clientId;
  }


  // =========================================================
  // SCRIPT DE GOOGLE
  // =========================================================

  private cargarScript():
    Promise<void> {

    const ventana =
      window as WindowGoogle;

    if (
      ventana.google
        ?.accounts
        ?.id
    ) {
      return Promise.resolve();
    }

    const existente =
      document.getElementById(
        this.scriptId,
      ) as HTMLScriptElement | null;

    if (existente) {
      return new Promise<void>(
        (
          resolve,
          reject,
        ) => {

          const verificar = () => {
            const google =
              (
                window as WindowGoogle
              ).google;

            if (
              google
                ?.accounts
                ?.id
            ) {
              resolve();
            } else {
              reject(
                new Error(
                  'Google Identity Services no está disponible.',
                ),
              );
            }
          };

          existente.addEventListener(
            'load',
            verificar,
            {
              once: true,
            },
          );

          existente.addEventListener(
            'error',
            () => {
              reject(
                new Error(
                  'No fue posible cargar Google Identity Services.',
                ),
              );
            },
            {
              once: true,
            },
          );
        },
      );
    }

    return new Promise<void>(
      (
        resolve,
        reject,
      ) => {

        const script =
          document.createElement(
            'script',
          );

        script.id =
          this.scriptId;

        script.src =
          this.scriptUrl;

        script.async = true;
        script.defer = true;

        script.onload = () => {
          resolve();
        };

        script.onerror = () => {
          reject(
            new Error(
              'No fue posible cargar Google Identity Services.',
            ),
          );
        };

        document.head.appendChild(
          script,
        );
      },
    );
  }


  // =========================================================
  // BOTÓN
  // =========================================================

  async renderizarBoton(
    contenedor: HTMLElement,
    callback: (
      credential: string,
    ) => void,
    modo:
      | 'login'
      | 'register'
      = 'login',
  ): Promise<void> {

    const clientId =
      await this.obtenerClientId();

    await this.cargarScript();

    const google =
      (
        window as WindowGoogle
      ).google;

    if (
      !google
        ?.accounts
        ?.id
    ) {
      throw new Error(
        'Google Identity Services no está disponible.',
      );
    }

    google.accounts.id.initialize({
      client_id: clientId,

      callback: (
        response:
          GoogleCredentialResponse,
      ) => {

        const credential =
          response
            .credential
            ?.trim();

        if (!credential) {
          return;
        }

        callback(
          credential,
        );
      },
    });

    contenedor.innerHTML = '';

    const anchoDisponible =
      Math.round(
        contenedor
          .getBoundingClientRect()
          .width,
      );

    const ancho =
      Math.min(
        400,
        Math.max(
          240,
          anchoDisponible || 400,
        ),
      );

    google.accounts.id.renderButton(
      contenedor,
      {
        type: 'standard',
        theme: 'outline',
        size: 'large',

        text: 'continue_with',

        shape: 'rectangular',
        logo_alignment: 'left',
        width: ancho,
      },
    );
  }
}