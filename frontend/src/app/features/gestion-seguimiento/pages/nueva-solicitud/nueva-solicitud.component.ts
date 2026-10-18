import {
  AuthService,
} from '../../../../core/auth/auth.service';

import {
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';

import {
  CommonModule,
} from '@angular/common';

import {
  FormsModule,
} from '@angular/forms';

import {
  ActivatedRoute,
  Router,
  RouterLink,
} from '@angular/router';

import {
  Observable,
  of,
  switchMap,
} from 'rxjs';

import {
  ContactoSolicitud,
  GestionSeguimientoService,
  mensajeError,
} from '../../services/gestion-seguimiento.service';

import {
  Campo,
  Solicitud,
  Tramite,
  ValorDato,
} from '../../models/gestion-seguimiento.models';

import {
  IconoGestionComponent,
} from '../../components/icono-gestion/icono-gestion.component';


interface CarreraOpcion {
  valor: string;
  etiqueta: string;
}


interface CarreraGrupo {
  grupo: string;
  nombreCorto: string;

  opciones: CarreraOpcion[];
}


interface CorreoCuenta {
  correo: string;

  es_principal?: boolean;
  activo?: boolean;
  verificado?: boolean;
}


interface UsuarioConCorreos {
  nombres?: string;
  apellidos?: string;

  correos?: CorreoCuenta[];
}


interface SolicitudConContacto
  extends Solicitud {
  nombre_contacto?: string | null;
  telefono_contacto?: string | null;
  correo_contacto?: string | null;
}


@Component({
  selector:
    'app-preparar-solicitud',

  standalone: true,

  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    IconoGestionComponent,
  ],

  host: {
    class:
      'm03-view',
  },

  templateUrl:
    './nueva-solicitud.component.html',

  styleUrl:
    './nueva-solicitud.component.scss',
})
export class NuevaSolicitudComponent
  implements OnInit
{
  readonly auth =
    inject(
      AuthService,
    );

  private readonly api =
    inject(
      GestionSeguimientoService,
    );

  private readonly route =
    inject(
      ActivatedRoute,
    );

  private readonly router =
    inject(
      Router,
    );


  readonly solicitud =
    signal<Solicitud | null>(
      null,
    );

  readonly tramite =
    signal<Tramite | null>(
      null,
    );

  readonly aplicables =
    signal<Tramite | null>(
      null,
    );

  readonly ocupado =
    signal(
      false,
    );

  readonly error =
    signal(
      '',
    );

  readonly mensaje =
    signal(
      '',
    );

  readonly enviada =
    signal<Solicitud | null>(
      null,
    );

  readonly perfilCargado =
    signal(
      false,
    );


  valores: Record<
    number,
    ValorDato | null
  > = {};


  perfil: Record<
    string,
    string
  > = {
    carrera_programa:
      '',

    documento_identidad:
      '',
  };


  perfilGuardado: Record<
    string,
    string
  > = {
    carrera_programa:
      '',

    documento_identidad:
      '',
  };


  contacto: ContactoSolicitud = {
    nombre_contacto:
      '',

    telefono_contacto:
      '',

    correo_contacto:
      '',
  };


  contactoGuardado: ContactoSolicitud = {
    nombre_contacto:
      '',

    telefono_contacto:
      '',

    correo_contacto:
      '',
  };


  nombreCuentaPredeterminado =
    '';

  correoCuentaPredeterminado =
    '';


  readonly carreras: CarreraGrupo[] = [
    {
      grupo:
        'Ciencias de la Salud',

      nombreCorto:
        'Ciencias de la Salud',

      opciones: [
        {
          valor:
            'Medicina',

          etiqueta:
            'Medicina',
        },

        {
          valor:
            'Nutrición Clínica y Dietética',

          etiqueta:
            'Nutrición Clínica y Dietética',
        },
      ],
    },

    {
      grupo:
        'Ciencias Económicas, Administrativas y Financieras',

      nombreCorto:
        'Económicas y Financieras',

      opciones: [
        {
          valor:
            'Administración de Empresas',

          etiqueta:
            'Administración de Empresas',
        },

        {
          valor:
            'Contaduría Pública',

          etiqueta:
            'Contaduría Pública',
        },

        {
          valor:
            'Economía',

          etiqueta:
            'Economía',
        },

        {
          valor:
            'Economía e Inteligencia de Negocios',

          etiqueta:
            'Economía e Inteligencia de Negocios',
        },

        {
          valor:
            'Administración Turística',

          etiqueta:
            'Administración Turística',
        },

        {
          valor:
            'Ingeniería Comercial',

          etiqueta:
            'Ingeniería Comercial',
        },

        {
          valor:
            'Ingeniería en Innovación Empresarial',

          etiqueta:
            'Ingeniería en Innovación Empresarial',
        },

        {
          valor:
            'Marketing y Medios Digitales',

          etiqueta:
            'Marketing y Medios Digitales',
        },
      ],
    },

    {
      grupo:
        'Ingenierías y Tecnologías',

      nombreCorto:
        'Ingenierías y Tecnologías',

      opciones: [
        {
          valor:
            'Ingeniería Ambiental',

          etiqueta:
            'Ingeniería Ambiental',
        },

        {
          valor:
            'Ingeniería Biomédica',

          etiqueta:
            'Ingeniería Biomédica',
        },

        {
          valor:
            'Ingeniería Bioquímica y de Bioprocesos',

          etiqueta:
            'Ingeniería Bioquímica y de Bioprocesos',
        },

        {
          valor:
            'Ingeniería Civil',

          etiqueta:
            'Ingeniería Civil',
        },

        {
          valor:
            'Ingeniería de Sistemas',

          etiqueta:
            'Ingeniería de Sistemas',
        },

        {
          valor:
            'Ingeniería en Multimedia e Interactividad Digital',

          etiqueta:
            'Ingeniería en Multimedia e Interactividad Digital',
        },

        {
          valor:
            'Ingeniería Industrial',

          etiqueta:
            'Ingeniería Industrial',
        },

        {
          valor:
            'Ingeniería Química',

          etiqueta:
            'Ingeniería Química',
        },

        {
          valor:
            'Ingeniería Mecatrónica',

          etiqueta:
            'Ingeniería Mecatrónica',
        },

        {
          valor:
            'Ingeniería de Telecomunicaciones',

          etiqueta:
            'Ingeniería de Telecomunicaciones',
        },
      ],
    },

    {
      grupo:
        'Ciencias Sociales y Humanas',

      nombreCorto:
        'Sociales y Humanas',

      opciones: [
        {
          valor:
            'Comunicación Social',

          etiqueta:
            'Comunicación Social',
        },

        {
          valor:
            'Comunicación Digital Multimedia',

          etiqueta:
            'Comunicación Digital Multimedia',
        },

        {
          valor:
            'Psicología',

          etiqueta:
            'Psicología',
        },

        {
          valor:
            'Psicopedagogía',

          etiqueta:
            'Psicopedagogía',
        },
      ],
    },

    {
      grupo:
        'Derecho y Ciencias Políticas',

      nombreCorto:
        'Derecho y Ciencias Políticas',

      opciones: [
        {
          valor:
            'Ciencias Políticas y Relaciones Internacionales',

          etiqueta:
            'Ciencias Políticas y Relaciones Internacionales',
        },

        {
          valor:
            'Derecho',

          etiqueta:
            'Derecho',
        },
      ],
    },

    {
      grupo:
        'Arquitectura y Diseño',

      nombreCorto:
        'Arquitectura y Diseño',

      opciones: [
        {
          valor:
            'Arquitectura',

          etiqueta:
            'Arquitectura',
        },

        {
          valor:
            'Diseño Digital',

          etiqueta:
            'Diseño Digital',
        },

        {
          valor:
            'Diseño Gráfico y Comunicación Visual',

          etiqueta:
            'Diseño Gráfico y Comunicación Visual',
        },
      ],
    },
  ];


  readonly carrerasDisponibles: CarreraOpcion[] = this.carreras.flatMap(grupo => grupo.opciones);

  readonly camposPerfil = [
    {
      clave:
        'carrera_programa',

      etiqueta:
        'Carrera o programa',
    },

    {
      clave:
        'documento_identidad',

      etiqueta:
        'Documento de identidad',
    },
  ];


  ngOnInit() {
    const id = Number(
      this.route.snapshot
        .paramMap
        .get(
          'id',
        ),
    );

    this.ocupado.set(
      true,
    );

    this.api
      .detalle(
        id,
      )
      .pipe(
        switchMap(
          (solicitud) => {
            this.solicitud.set(
              solicitud,
            );

            if (
              solicitud.estado !==
              'borrador'
            ) {
              this.router.navigate([
                '/solicitudes',
                id,
              ]);
            }

            solicitud.datos.forEach(
              (dato) => {
                this.valores[
                  dato.id_campo
                ] =
                  dato.valor;
              },
            );

            this.inicializarContacto(
              solicitud,
            );

            return this.api.tramite(
              solicitud.id_tramite,
            );
          },
        ),
      )
      .subscribe({
        next: (tramite) => {
          this.tramite.set(
            tramite,
          );

          this.ocupado.set(
            false,
          );
        },

        error: (e) =>
          this.fallar(
            e,
          ),
      });

    this.api
      .get<Record<string, string>>(
        'users/me/perfil-academico',
      )
      .subscribe({
        next: (perfil) => {
          this.camposPerfil.forEach(
            (campo) => {
              this.perfil[
                campo.clave
              ] =
                perfil[
                  campo.clave
                ] || '';
            },
          );

          this.perfilGuardado = {
            ...this.perfil,
          };

          this.perfilCargado.set(
            true,
          );
        },

        error: (e) => {
          this.perfilCargado.set(
            true,
          );

          if (
            e.status !==
            404
          ) {
            this.error.set(
              mensajeError(
                e,
              ),
            );
          }
        },
      });
  }


  // =========================================================
  // CONTACTO
  // =========================================================


  private inicializarContacto(
    solicitud: Solicitud,
  ) {
    const usuario =
      this.auth.usuarioActual() as
        UsuarioConCorreos | null;

    this.nombreCuentaPredeterminado = [
      usuario?.nombres,
      usuario?.apellidos,
    ]
      .filter(
        Boolean,
      )
      .join(
        ' ',
      )
      .trim();

    this.correoCuentaPredeterminado =
      this.obtenerCorreoCuenta(
        usuario,
      );

    const solicitudContacto =
      solicitud as
        SolicitudConContacto;

    this.contacto = {
      nombre_contacto:
        solicitudContacto
          .nombre_contacto
          ?.trim()
        ||
        this.nombreCuentaPredeterminado,

      telefono_contacto:
        solicitudContacto
          .telefono_contacto
          ?.trim()
        ||
        '',

      correo_contacto:
        solicitudContacto
          .correo_contacto
          ?.trim()
        ||
        this.correoCuentaPredeterminado,
    };

    /*
     * Aquí guardamos exactamente lo que existe en BD.
     *
     * Si todavía no había contacto persistido, los valores
     * autocompletados quedarán como cambios pendientes y se
     * guardarán cuando el estudiante consulte requisitos.
     */
    this.contactoGuardado = {
      nombre_contacto:
        solicitudContacto
          .nombre_contacto
          ?.trim()
        ||
        '',

      telefono_contacto:
        solicitudContacto
          .telefono_contacto
          ?.trim()
        ||
        '',

      correo_contacto:
        solicitudContacto
          .correo_contacto
          ?.trim()
        ||
        '',
    };
  }


  private obtenerCorreoCuenta(
    usuario:
      UsuarioConCorreos | null,
  ): string {
    const correos =
      usuario?.correos || [];

    const principal =
      correos.find(
        (correo) =>
          correo.es_principal ===
            true &&
          correo.activo !==
            false,
      );

    if (
      principal?.correo
    ) {
      return principal.correo;
    }

    const verificado =
      correos.find(
        (correo) =>
          correo.verificado ===
            true &&
          correo.activo !==
            false,
      );

    if (
      verificado?.correo
    ) {
      return verificado.correo;
    }

    return (
      correos[0]?.correo
      || ''
    );
  }


  nombreContactoModificado():
    boolean {
    if (
      !this.nombreCuentaPredeterminado
    ) {
      return false;
    }

    return (
      this.contacto
        .nombre_contacto
        .trim() !==
      this.nombreCuentaPredeterminado
        .trim()
    );
  }


  correoContactoModificado():
    boolean {
    if (
      !this.correoCuentaPredeterminado
    ) {
      return false;
    }

    return (
      this.contacto
        .correo_contacto
        .trim()
        .toLowerCase() !==
      this.correoCuentaPredeterminado
        .trim()
        .toLowerCase()
    );
  }


  nombreContactoValido():
    boolean {
    const valor =
      this.contacto
        .nombre_contacto
        .trim();

    return (
      valor.length >= 2 &&
      /[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/u
        .test(
          valor,
        )
    );
  }


  telefonoContactoValido():
    boolean {
    const telefono =
      this.contacto
        .telefono_contacto
        .trim();

    if (
      !/^[0-9+\-().\s]+$/
        .test(
          telefono,
        )
    ) {
      return false;
    }

    const digitos =
      telefono.replace(
        /\D/g,
        '',
      );

    return (
      digitos.length >= 7 &&
      digitos.length <= 15
    );
  }


  correoContactoValido():
    boolean {
    const correo =
      this.contacto
        .correo_contacto
        .trim();

    return (
      /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        .test(
          correo,
        )
    );
  }


  contactoCompleto():
    boolean {
    return (
      this.nombreContactoValido() &&
      this.telefonoContactoValido() &&
      this.correoContactoValido()
    );
  }


  // =========================================================
  // PERFIL
  // =========================================================


  perfilCompleto():
    boolean {
    const carrera =
      this.perfil[
        'carrera_programa'
      ]?.trim();

    const ci =
      this.perfil[
        'documento_identidad'
      ]?.trim();

    return Boolean(
      carrera &&
      this.carrerasDisponibles.some(
        opcion => opcion.valor === carrera
      ) &&
      ci &&
      ci.length >= 3
    );
  }


  perfilPendienteDeGuardar():
    boolean {
    return this.camposPerfil.some(
      (campo) => {
        const actual =
          this.perfil[
            campo.clave
          ]?.trim() || '';

        const guardado =
          this.perfilGuardado[
            campo.clave
          ] || '';

        return (
          actual !==
          guardado
        );
      },
    );
  }


  private datosPerfilModificados():
    Record<
      string,
      string | null
    > {
    return Object.fromEntries(
      this.camposPerfil
        .filter(
          (campo) => {
            const actual =
              this.perfil[
                campo.clave
              ]?.trim() || '';

            const guardado =
              this.perfilGuardado[
                campo.clave
              ] || '';

            return (
              actual !==
              guardado
            );
          },
        )
        .map(
          (campo) => [
            campo.clave,

            this.perfil[
              campo.clave
            ]?.trim()
            ||
            null,
          ],
        ),
    );
  }


  private actualizarPerfilLocal(
    datos: Record<
      string,
      string | null
    >,
  ) {
    Object.entries(
      datos,
    ).forEach(
      ([
        clave,
        valor,
      ]) => {
        const texto =
          valor || '';

        this.perfilGuardado[
          clave
        ] =
          texto;

        this.perfil[
          clave
        ] =
          texto;
      },
    );
  }


  // =========================================================
  // CAMPOS DINÁMICOS
  // =========================================================


  valorAutomatico(
    campo: Campo,
  ): ValorDato | null {
    const actual =
      this.valores[
        campo.id_campo
      ];

    if (
      actual !== undefined &&
      actual !== null &&
      actual !== ''
    ) {
      return null;
    }

    const usuario =
      this.auth.usuarioActual();

    const valorPerfil =
      this.perfilGuardado[
        campo.clave
      ];

    const valorUsuario =
      campo.clave ===
        'nombres'
        ? usuario?.nombres
        : campo.clave ===
            'apellidos'
          ? usuario?.apellidos
          : null;

    const valor =
      valorPerfil ||
      valorUsuario;

    return (
      campo.tipo_dato ===
        'texto' &&
      valor
    )
      ? valor
      : null;
  }


  camposSolicitados():
    Campo[] {
    const clavesPerfil =
      new Set(
        this.camposPerfil.map(
          (campo) =>
            campo.clave,
        ),
      );

    return (
      this.tramite()
        ?.campos
      ||
      []
    ).filter(
      (campo) =>
        !clavesPerfil.has(
          campo.clave,
        ) &&
        this.valorAutomatico(
          campo,
        ) ===
        null,
    );
  }


  opciones(
    campo: Campo,
  ) {
    return (
      campo.configuracion
        ?.opciones
      ||
      []
    ).map(
      (opcion) =>
        typeof opcion ===
        'string'
          ? {
              valor:
                opcion,

              etiqueta:
                opcion,
            }
          : {
              valor:
                opcion.valor,

              etiqueta:
                opcion.etiqueta
                ||
                opcion.valor,
            },
    );
  }


  camposAdicionalesCompletos():
    boolean {
    return this.camposSolicitados()
      .filter(
        (campo) =>
          campo.obligatorio,
      )
      .every(
        (campo) => {
          const valor =
            this.valores[
              campo.id_campo
            ];

          return (
            valor !== undefined &&
            valor !== null &&
            String(
              valor,
            ).trim() !== ''
          );
        },
      );
  }


  // =========================================================
  // ESTADO DEL FORMULARIO
  // =========================================================


  formularioCompleto():
    boolean {
    return (
      this.contactoCompleto() &&
      this.perfilCompleto() &&
      this.camposAdicionalesCompletos()
    );
  }


  puedeConsultar():
    boolean {
    return (
      this.perfilCargado() &&
      this.formularioCompleto() &&
      !this.ocupado()
    );
  }


  puedeEnviar():
    boolean {
    return Boolean(
      this.aplicables() &&
      this.formularioCompleto() &&
      !this.ocupado()
    );
  }


  cambiar() {
    this.aplicables.set(
      null,
    );

    this.mensaje.set(
      '',
    );

    this.error.set(
      '',
    );
  }


  // =========================================================
  // GUARDAR Y CONSULTAR
  // =========================================================


  guardar() {
    if (
      this.ocupado() ||
      !this.perfilCargado()
    ) {
      return;
    }

    const solicitud =
      this.solicitud();

    if (
      !solicitud
    ) {
      return;
    }

    if (
      !this.contactoCompleto()
    ) {
      this.error.set(
        'Completa correctamente el nombre, teléfono y correo de contacto.',
      );

      return;
    }

    if (
      !this.perfilCompleto()
    ) {
      this.error.set(
        'Selecciona tu carrera o programa e ingresa tu documento de identidad.',
      );

      return;
    }

    if (
      !this.camposAdicionalesCompletos()
    ) {
      this.error.set(
        'Completa los datos obligatorios del trámite antes de consultar los requisitos.',
      );

      return;
    }

    this.ocupado.set(
      true,
    );

    this.error.set(
      '',
    );

    this.mensaje.set(
      '',
    );

    this.aplicables.set(
      null,
    );

    const datosPerfil =
      this.datosPerfilModificados();

    let guardarPerfil$:
      Observable<unknown>;

    if (
      Object.keys(
        datosPerfil,
      ).length
    ) {
      guardarPerfil$ =
        this.api.patch(
          'users/me/perfil-academico',
          datosPerfil,
        );
    } else {
      guardarPerfil$ =
        of(
          null,
        );
    }

    guardarPerfil$
      .pipe(
        switchMap(
          () => {
            if (
              Object.keys(
                datosPerfil,
              ).length
            ) {
              this.actualizarPerfilLocal(
                datosPerfil,
              );
            }

            return this.api.guardar(
              solicitud.id_solicitud,

              this.construirDatosSolicitud(),

              {
                nombre_contacto:
                  this.contacto
                    .nombre_contacto
                    .trim(),

                telefono_contacto:
                  this.contacto
                    .telefono_contacto
                    .trim(),

                correo_contacto:
                  this.contacto
                    .correo_contacto
                    .trim(),
              },
            );
          },
        ),

        switchMap(
          (actualizada) => {
            this.solicitud.set(
              actualizada,
            );

            this.contactoGuardado = {
              nombre_contacto:
                this.contacto
                  .nombre_contacto
                  .trim(),

              telefono_contacto:
                this.contacto
                  .telefono_contacto
                  .trim(),

              correo_contacto:
                this.contacto
                  .correo_contacto
                  .trim(),
            };

            return this.api.preparacion(
              solicitud.id_solicitud,
            );
          },
        ),
      )
      .subscribe({
        next: (tramite) => {
          this.aplicables.set(
            tramite,
          );

          this.mensaje.set(
            'Datos registrados. Revisa los requisitos antes de enviar la solicitud.',
          );

          this.ocupado.set(
            false,
          );
        },

        error: (e) =>
          this.fallar(
            e,
          ),
      });
  }


  private construirDatosSolicitud(): {
    id_campo: number;
    valor: ValorDato;
  }[] {
    const datos: {
      id_campo: number;
      valor: ValorDato;
    }[] = [];

    for (
      const campo of
      this.tramite()
        ?.campos
      ||
      []
    ) {
      const valor =
        this.valorAutomatico(
          campo,
        )
        ??
        this.valores[
          campo.id_campo
        ];

      if (
        valor === undefined ||
        valor === null ||
        valor === ''
      ) {
        continue;
      }

      datos.push({
        id_campo:
          campo.id_campo,

        valor:
          campo.tipo_dato ===
              'entero' ||
            campo.tipo_dato ===
              'decimal'
            ? Number(
                valor,
              )
            : valor,
      });
    }

    return datos;
  }


  // =========================================================
  // ENVÍO
  // =========================================================


  enviar() {
    const solicitud =
      this.solicitud();

    if (
      !solicitud ||
      !this.puedeEnviar()
    ) {
      return;
    }

    this.ocupado.set(
      true,
    );

    this.error.set(
      '',
    );

    this.api
      .enviar(
        solicitud.id_solicitud,
      )
      .subscribe({
        next: (enviada) => {
          this.enviada.set(
            enviada,
          );

          this.ocupado.set(
            false,
          );
        },

        error: (e) =>
          this.fallar(
            e,
          ),
      });
  }


  // =========================================================
  // PRESENTACIÓN
  // =========================================================


  formatearNumeroSolicitud(
    id: number,
  ): string {
    return String(
      id,
    ).padStart(
      4,
      '0',
    );
  }


  mensajeTrasEnvio():
    string {
    return (
      'Tu solicitud fue registrada correctamente. ' +
      'Revisa el seguimiento para completar el pago, ' +
      'la entrega de documentación u otras acciones ' +
      'pendientes que correspondan al trámite.'
    );
  }


  private fallar(
    e: Parameters<
      typeof mensajeError
    >[0],
  ) {
    this.error.set(
      mensajeError(
        e,
      ),
    );

    this.ocupado.set(
      false,
    );
  }
}