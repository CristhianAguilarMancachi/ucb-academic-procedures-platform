# M03 — Implementación de las 13 referencias visuales

## Corrección puntual del layout global — 16/09/2026

Se restauraron los nueve archivos de `main-layout`, `app-header` y `app-sidebar` a su estructura, comportamiento y apariencia anteriores a la adaptación visual. Ocho son idénticos a la referencia original de Git; el HTML del header mantiene únicamente el enlace real a `/tramites` para solicitante/administrador y formato. El Panel Administrativo conserva `/admin/usuarios` y su condición original de administrador. Se retiraron `m03-layout`, el menú móvil específico, la tarjeta de cuenta del sidebar, su logout duplicado y los estilos globales específicos de M03. El footer original no cambió.

Las trece referencias siguen implementadas dentro del contenido M03. Solo se ajustaron las condiciones de creación del catálogo y el enlace de nueva solicitud desde un detalle administrativo. Los estilos `.m03-view`, modales y timeline se conservan.

| Rol único | Opciones M03 |
|---|---|
| Solicitante | Nuevo trámite, solicitudes propias, seguimiento, observaciones, cancelación y factura cuando correspondan; sin administración |
| Personal administrativo | Bandeja y detalle administrativos con sus acciones; sin accesos a solicitudes propias ni configuración |
| Administrador | Gestión administrativa, configuración y capacidades de solicitudes propias que ya tenía; Panel Administrativo original |

Se conservan `authGuard`, `roleGuard`, `AuthService` y el filtrado original del sidebar. Las cuatro rutas de solicitudes propias admiten solicitante/administrador; las dos administrativas admiten personal administrativo/administrador; configuración admite administrador. Las cinco opciones M03 del menú coinciden con esa separación. Los roles múltiples conservan la unión de capacidades del mecanismo existente. El catálogo continúa público, sin acción de solicitar para personal administrativo sin otro rol habilitado.

**Límite de esta corrección:** `exigir_solicitante` en el backend sigue autorizando los tres roles funcionales. No se modificó esa política. La restricción adicional para personal administrativo se aplica a navegación, acciones y rutas Angular; no constituye una revocación de su permiso directo de API.

Validación: comparación de restauración contra Git, huellas de backend/SQL/footer sin cambios, matriz estática de siete rutas y cinco opciones M03, `git diff --check` y build de producción Angular en Docker correctos. Prettier se ejecutó únicamente sobre los seis archivos editados que requerían formato. No se instalaron dependencias, no se inició PostgreSQL y no se ejecutó SQL. La navegación autenticada en navegador no fue probada.

## Alcance

Se adaptó el frontend existente, conservando APIs, permisos, estados y transiciones. No se modificaron backend, SQL, dependencias ni PostgreSQL en esta tarea. Los cambios backend que figuran en el árbol de trabajo pertenecen a la implementación anterior.

La apariencia utiliza fondos azul oscuro, acentos amarillos/azules, tarjetas, tablas, badges, timeline, navegación y diálogos basados en las referencias. La fidelidad visual en navegador aún no fue comprobada; el build confirma compilación, no equivalencia de píxeles ni aceptación funcional.

## Cobertura

| Ref. | Tipo | Componente / ubicación | Comportamiento |
|---|---|---|---|
| 1 | Página | `catalogo.component`, `/tramites` y `/tramites/:id` | Selección, información, requisitos y creación real de borrador; preparación en `/solicitudes/:id/preparar` |
| 2 | Modal | Catálogo + `gestion-modal.component` | Detalle de requisitos, costos individuales, pasos y atención publicados |
| 3 | Confirmación | Variante de `preparar.component` | Se muestra solo tras envío exitoso; ID, trámite, fecha de envío y usuario autenticado reales |
| 4 | Página | `solicitudes-lista.component`, `/mis-solicitudes` | Tabla, estado, fechas, filtro y navegación |
| 5 | Página | `solicitud-detalle.component`, `/solicitudes/:id` | Timeline público, progreso, requisitos, observaciones y factura posterior |
| 6 | Modal | Detalle propio | Cancelación con motivo y reglas existentes |
| 7 | Variante | Mismo detalle propio | Alerta de cierre, historial real y etapas sin continuidad; sin alterar sus estados persistidos |
| 8 | Página | Misma lista, `/admin/solicitudes` | Filtros reales, tabla administrativa y recuentos claramente acotados |
| 9 | Página | Mismo detalle, `/admin/solicitudes/:id` | Perfil, datos, requisitos, pagos, recepción, avance, observaciones e historial completo |
| 10 | Modal | Detalle administrativo | Confirmación de recepción de un requisito físico por operación |
| 11 | Modal | Detalle administrativo | Rechazo con motivo obligatorio |
| 12 | Modal | Detalle administrativo | Resultado y estado derivado de modalidad; confirmación explícita |
| 13 | Modal | Detalle administrativo | Entrega a titular/tercero, datos del receptor y finalización |

**Las referencias 1–13 tienen representación implementada.** No se crearon trece rutas ni se duplicaron pantallas por estado.

## Componentes y reutilización

Nuevos, en `frontend/src/app/features/gestion-seguimiento/`:

- `gestion-modal.component.ts`: diálogo nativo, fondo atenuado, foco confinado por `showModal`, restauración de foco, Escape y cierre bloqueados durante peticiones; variante amplia para requisitos.
- `gestion-timeline.component.ts`: historial y etapas de solicitante/administración; actores internos solo en vista administrativa.
- `gestion-icon.component.ts`: iconos del paquete `@ng-icons` ya instalado.

Adaptados:

- `catalogo.component.ts/html`: selección y detalle modal.
- `preparar.component.ts/html`: mantiene datos dinámicos, perfil y facturas; incorpora confirmación del envío.
- `solicitudes-lista.component.ts/html`: tablas y recuentos de la página actual.
- `solicitud-detalle.component.ts/html`: composición por rol, timeline y cinco modales operativos; se mantienen todas las acciones previas.
- `configuracion.component.ts`: adopta el estilo compartido; formulario existente conservado. HTML y servicio recibieron formato, sin cambiar su lógica.
- `gestion.models.ts`: fecha de actualización opcional donde el API la expone y etiquetas de estados reales.
- `main-layout.*`, `app-header.*`, `app-sidebar.*`: restaurados al layout global original en la corrección puntual descrita arriba. Se mantienen la integración de rutas M03 y los guards existentes.
- `sidebar-menu.config.ts`: acceso “Nuevo trámite”.

Estilos:

- `gestion.scss` contiene un mixin compartido.
- `frontend/src/styles.scss` lo emite una sola vez bajo `.m03-view`, evitando duplicar CSS por componente y sin ampliar presupuestos del build.
- Las reglas responsive del contenido M03 permiten una columna y tablas desplazables. El layout exterior conserva sus reglas originales; se eliminaron las extensiones `.m03-layout`.

## APIs existentes utilizadas

Todas bajo `/api`, mediante el servicio/interceptores existentes:

- `GET /tramites`, `GET /tramites/{id}`.
- `POST /solicitudes`, `GET/PATCH /solicitudes/{id}`, `GET /solicitudes/mias`.
- `GET /solicitudes/{id}/preparacion`, `POST /solicitudes/{id}/enviar`.
- `GET /solicitudes/{id}/seguimiento`, `POST /solicitudes/{id}/cancelar`.
- `PUT /solicitudes/{id}/requisitos/{requisito}/factura`.
- `GET/PATCH /users/me/perfil-academico`; identidad de la sesión restaurada por `AuthService`.
- `GET /admin/solicitudes`, `GET /admin/solicitudes/{id}`.
- Acciones POST bajo `/admin/solicitudes/{id}`: `recibir`, `iniciar`, `avanzar`, `rechazar`, `finalizar`, `entregar`, `observaciones`, `observaciones/{observacion}/resolver`.
- Acciones POST por requisito: `presentacion`, `verificar`, `verificar-pago`.
- Se conserva la configuración M05 mediante las rutas administrativas existentes.

## Diferencias deliberadas y límites reales de datos

- “Ticket” se sustituye por solicitud e ID real; no se generan códigos ni datos de muestra.
- No existe estado `observada` ni `pendiente_pago`: las observaciones se muestran aparte del estado real.
- Cancelar exige motivo y se limita a borrador/pendiente sin factura; se conserva la validación final del backend.
- No se ofrece selección arbitraria de estados ni saltos de etapa.
- La finalización deriva de la modalidad capturada. Solo las solicitudes antiguas sin modalidad permiten elegirla explícitamente.
- La entrega se registra desde `lista_para_entrega`; el registro finaliza la solicitud. No se permite una entrega posterior a `finalizada` como sugiere una imagen.
- Presentación y entrega usan la fecha registrada por el servidor. No se implementaron fechas retroactivas; la presentación física es individual y no acredita automáticamente el requisito. No se agregó una observación de recepción que el contrato de ese endpoint no admite.
- La bandeja administrativa no ofrece nombre/correo del solicitante ni fecha de actualización: muestra ID de usuario y fecha de envío. El detalle sí muestra el nombre/perfil disponible.
- Las listas no ofrecen etapa actual, siguiente acción u observaciones agregadas. Esos datos se consultan en el detalle; no se generan peticiones adicionales por cada fila.
- No hay endpoint de métricas globales por estado. Se muestra el total del filtro y recuentos de la página actual, sin presentarlos como totales globales. No se inventa un total de observados.
- La búsqueda por texto se limita explícitamente a la página cargada. Los filtros administrativos por IDs, estado y fechas siguen consultando al servidor. No se simula búsqueda global ni ordenamiento no soportado.
- Los importes se muestran por requisito y gestión, sin inventar un costo total universal para requisitos condicionales. Direcciones, horarios e instrucciones solo aparecen si están publicados.
- No se añadieron notificaciones, carga de documentos, enlaces institucionales ni estadísticas inexistentes para reproducir detalles de las imágenes.

## Verificaciones

- Revisados Compose, Dockerfiles y dependencias existentes; sin instalaciones locales.
- `docker compose config --quiet`: correcto.
- Docker inicialmente requirió permiso de acceso al socket; después respondió sin contenedores activos y con imagen frontend disponible.
- La versión instalada de Compose no admite `run --no-build`. Se usó la imagen existente con `--pull never`, sin `--build` y con `--no-deps`.
- Build de producción ejecutado dentro de Docker. Los dos imports incorrectos detectados en el primer intento fueron corregidos. La advertencia inicial de CSS fue resuelta centralizando el estilo, sin modificar presupuestos.
- Prettier disponible en la imagen utilizado para dar formato al frontend, sin descargar paquetes.
- `git diff --check`: correcto sobre archivos rastreados.

Comando de build:

```sh
docker compose run --rm --no-deps --pull never -T frontend npm run build
```

No se arrancaron backend, PostgreSQL ni servicios dependientes. No se ejecutó SQL. Solo se usaron contenedores frontend temporales para formato/compilación; el build genera `frontend/dist/` y la caché normal de Angular.

Pendientes: inspección en navegador de las trece variantes, responsive y teclado; escenarios con usuarios reales de ambos roles, errores de API y transiciones sobre una base preparada por el usuario. Estas comprobaciones no se afirman realizadas.
