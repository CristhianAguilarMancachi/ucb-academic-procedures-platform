# M03 — Fases 4, 5 y 6

## Revisión final dirigida antes del SQL — 20/09/2026

Esta sección actualiza las decisiones y resultados anteriores de este documento.

- El único parche sigue siendo `backend/sql/manual/gestion_seguimiento_fases_4_5_6.sql`, editado directamente y aún sin ejecutar. `database.sql` refleja los mismos cambios y conserva las definiciones F1–3.
- Nueva CHECK: `en_proceso` exige `id_etapa_actual`. Al terminar la última etapa, se conserva su ID aunque la etapa quede completada, hasta registrar resultado. No se introduce otro estado ni se entrega/finaliza automáticamente. El frontend distingue una etapa en curso de una completada.
- Históricos sin etapas permanecen en revisión y pueden registrar resultado desde allí después de cumplir requisitos y resolver observaciones; no pasan a proceso sin etapa y no reciben backfill. La modalidad faltante se elige explícitamente.
- Nuevos índices únicos parciales por solicitud para etapa inicial y final; se conserva el de etapa en curso.
- `tramite_requisito` referencia `(id_tramite, id_etapa)` con FK compuesta; `tramite_etapa` incorpora la UNIQUE correspondiente. La validación de pertenencia del service de configuración ya existía y se conserva.
- `solicitud_historial` incorpora referencias opcionales de etapa/requisito y FKs compuestas por solicitud. Se utilizan en facturas, presentación, verificación manual/pago, etapas, observaciones/resolución, rechazo y resultado cuando existe referencia. La respuesta administrativa las expone; el historial público conserva su contrato y visibilidad.
- Un error de API de pagos deja el requisito pendiente y limpia la acreditación vigente no exitosa; preserva los intentos anteriores. Una factura ya acreditada conserva el camino idempotente anterior.
- Se verificaron los snapshots del envío, las condiciones simples tipadas y los pagos posteriores sin exigir factura inicial. No se crearon nuevas rutas, tablas ni sistemas de pago.
- Se confirmó que layout, sidebar y footer ya estaban restaurados. No se volvieron a modificar. Se conservan las trece interfaces y los guards existentes. Administrador conserva sus capacidades; solicitante no accede a rutas administrativas; personal administrativo usa el flujo administrativo. La autorización backend de solicitudes propias para los tres roles sigue siendo la política previa y no cambió.

Archivos backend modificados en esta revisión:

- Models: `solicitud.py`, `solicitud_etapa.py`, `solicitud_historial.py`, `tramite_etapa.py`, `tramite_requisito.py`.
- Schema: `seguimiento.py` (referencias opcionales del historial administrativo).
- Repository: `seguimiento_repository.py`.
- Services: `seguimiento_service.py`, `solicitud_service.py`, `solicitud_administrativa_service.py`, `pago_verificacion_service.py`.
- Validación: `scripts/verificar_m03.py`, `tests/test_gestion_seguimiento.py`.
- Ninguna route modificada. Los endpoints existentes de inicio, avance, resultado, verificación e historial conservan sus rutas; cambian las reglas internas descritas arriba.

Frontend modificado: `solicitud-detalle.component.ts`, `solicitud-detalle.component.html` y `gestion.models.ts`. Solo se adaptaron disponibilidad de inicio/avance/resultado y referencias opcionales del historial administrativo.

Validaciones actuales:

- Docker backend, sin conexiones: 146 fuentes compiladas en memoria; imports y `configure_mappers` correctos; 18 modelos M03 y cinco tablas nuevas coherentes; FKs compuestas e índices únicos revisados; OpenAPI con 40 rutas y 47 operaciones.
- 32 pruebas `unittest` con repositorios/HTTP en memoria: correctas. Incluyen continuidad de la referencia en cada flush, última etapa, resultado histórico, referencias de presentación y timeout de pagos.
- Docker frontend: Prettier sobre los tres archivos cambiados y build de producción correctos, sin errores ni advertencias de compilación.
- Comparación textual: F1–3 versionado más manual coincide con maestro para 27 tablas, columnas, tipos, defaults, constraints, índices, funciones, triggers y roles; orden de creación de referencias correcto. Se preserva la exclusión previa de semillas de personas.
- Layout original y siete rutas con `authGuard`/`roleGuard` comprobados estáticamente; `git diff --check` correcto.

No se ejecutó SQL, no se modificó PostgreSQL y no se instalaron dependencias. No se iniciaron endpoints ni servidores. La aplicación física, navegación con datos reales y concurrencia PostgreSQL siguen pendientes de la ejecución manual. Si la base difiere de F1–3 o contiene estados introducidos manualmente incompatibles con las nuevas restricciones, la transacción puede rechazarse; el script no altera datos históricos para ocultarlo.

## Estado de la entrega

Implementación de backend, configuración necesaria M05-F01–F07 e integración Angular mínima. El esquema nuevo **no fue aplicado**. No se ejecutó SQL, psql, Alembic, migraciones, `create_all`, servidores ni APIs que utilicen las tablas nuevas.

**Ejecuta manualmente en pgAdmin: `backend/sql/manual/gestion_seguimiento_fases_4_5_6.sql`.**

`backend/database.sql` es la referencia consolidada para crear una base nueva, no un parche para la base existente. Contiene las 27 tablas del alcance previo de acceso/cuenta y M03 ampliado, sin personas de ejemplo. Conserva los roles existentes. No amplía ni intenta reproducir el esquema RAG/chat ajeno a esta entrega.

La aceptación funcional queda pendiente de aplicar el SQL y probar los escenarios de este documento. Las verificaciones restantes deben realizarse en Docker Compose. El backend dispone de Python 3.12 y de `python-multipart` mediante su Dockerfile y requirements.txt; el frontend dispone de Node 24 y sus dependencias mediante su Dockerfile. No se requieren instalaciones en macOS ni un entorno temporal adicional.

En la revisión más reciente, `docker compose config --quiet` terminó correctamente, pero `docker compose ps` no pudo conectar: falta el socket del daemon del contexto activo `desktop-linux` (`~/.docker/run/docker.sock`). No se iniciaron servicios ni se instalaron dependencias fuera de Docker. Por esta limitación quedan pendientes el preflight completo, las pruebas en el contenedor backend y el build Angular dentro del contenedor frontend.

## 1. Fases 1–3 encontradas y conservadas

- Catálogo y configuración de trámites, requisitos, costos por gestión, campos, unidades y plantillas de etapas.
- Perfil académico, creación de borrador antes del pago, edición de datos, envío, fotografía de requisitos y consulta de solicitudes propias.
- Bandeja administrativa, recepción inicial, verificación manual no económica y verificación de facturas por HTTP con registro de intentos y protección de reutilización.
- No había ejecución de etapas, observaciones, resultado final ni entrega operacional.
- Angular tenía acceso/cuenta, usuarios y RAG; el menú de trámites apuntaba a rutas todavía no implementadas.

Se conservaron la eliminación de borradores, los permisos existentes, la auditoría y el servicio HTTP independiente de pagos. `pago_api_client.py` y `backend/mock_pago_api/` no se sustituyeron ni modificaron.

## 2. Fase 4 — Ejecución y seguimiento

- Nuevas etapas operacionales copiadas desde las etapas activas al enviar. Copia de nombre, descripción, unidad opcional, orden, inicial/final y visibilidad pública.
- Asociación de cada requisito aplicable con su etapa copiada; un requisito sin etapa es inicial.
- Inicio en `en_revision`, después de verificar requisitos iniciales obligatorios y resolver observaciones. Transición a `en_proceso` y comienzo de la primera etapa.
- Avance lineal por orden, con comprobación de requisitos iniciales y de la etapa actual, incluidos pagos posteriores y presentación física.
- El cliente debe enviar la etapa que pretende completar. Repetir una petición antigua no completa accidentalmente la siguiente etapa.
- Una sola etapa en curso mediante índice único parcial; pertenencia a solicitud mediante FKs compuestas.
- Seguimiento propio con estado, etapas públicas, porcentaje de etapas completadas, observaciones, resultado e historial visible.
- Historial funcional independiente de auditoría. Etapas internas generan eventos administrativos sin exponer su nombre al solicitante.

El porcentaje representa etapas completadas, no tiempo transcurrido ni un indicador M06. Después de registrar resultado vale 100%, aunque una modalidad con entrega aún espere recojo.

## 3. Fase 5 — Observaciones, cancelación y rechazo

- Observaciones generales o relacionadas con etapa/requisito, detalle, corrección requerida y canal opcional.
- Estados `pendiente` y `resuelta`, actores y fechas. La resolución la registra administración.
- Las observaciones pendientes bloquean inicio, avance y finalización, sin mover ni retroceder la etapa.
- Cancelación propia en borrador o pendiente de recepción, bloqueada ante factura registrada o pago acreditado. Se solicita motivo para el historial.
- Rechazo administrativo motivado en pendiente de recepción, revisión o proceso. No se admite sobre estados terminales.
- Al rechazar se conserva la etapa que estaba en curso como evidencia; no se marca completada artificialmente.

No existe estado persistido `observada`, subida de documentos, subsanación mediante archivos ni reembolsos.

## 4. Fase 6 — Resultado, entrega y finalización

- Modalidad configurada en trámite y copiada a la solicitud al enviar: `entrega`, `resultado_registrado` o `externo`.
- Completar la última etapa no cierra automáticamente la solicitud.
- Registrar resultado exige etapas completas, requisitos obligatorios cumplidos y ausencia de observaciones pendientes.
- `entrega`: pasa a `lista_para_entrega`; la entrega/recojo único la lleva a `finalizada`.
- Las otras modalidades finalizan al registrar el resultado.
- Entrega a titular o tercero; nombre obligatorio para tercero, documento y detalle opcionales.
- Resultado y entrega únicos por solicitud, actores, fechas, historial y auditoría.

La modalidad `externo` registra una confirmación administrativa; no integra automáticamente otro sistema.

## 5. Integraciones y correcciones de Fases 1–3

1. El envío exige factura únicamente para requisitos económicos **iniciales** obligatorios aplicables. Los posteriores se copian sin factura y pueden completarse al llegar a su etapa.
2. Las condiciones admiten solamente igualdad sobre un campo del formulario o uno de los cinco campos existentes del perfil académico. Se valida también el tipo y, si corresponde, las opciones del campo.
3. Falta de un dato necesario para evaluar una condición produce un error explícito; no se omite silenciosamente el requisito. Una condición falsa excluye ese requisito del snapshot.
4. El formulario guarda claves y etiquetas al enviar, y la solicitud conserva el nombre del trámite y modalidad. Si cambian los campos activos durante la preparación, se exige guardar el formulario vigente antes de enviar.
5. Presentación física y verificación administrativa son datos separados. Una nueva presentación actualiza fecha/actor y genera historial sin acreditar automáticamente el requisito.
6. Verificación manual y pago admiten `en_proceso`, pero únicamente para requisitos iniciales o de la etapa actual. La acreditación exige presentación previa cuando esté configurada.
7. Facturas acreditadas no pueden sustituirse; la repetición de una verificación exitosa devuelve el resultado existente sin consultar otra vez la API. Se mantiene el índice único global de factura acreditada.
8. Un error de API registra un intento `error` y deja el requisito `pendiente`, sin acreditarlo; los intentos previos se conservan.
9. Los campos incompatibles de respuestas inválidas de pago no se fuerzan en columnas normalizadas. Se preserva la respuesta completa en el JSON del intento; evita confundir errores de constraints con reutilización de factura.
10. Creación, envío, registro de factura, recepción y verificaciones generan historial desde ahora, sin eventos retroactivos.
11. Las mutaciones adquieren bloqueo de la fila de solicitud. Estado, historial y auditoría se confirman en la misma transacción. El índice de factura protege también solicitudes concurrentes distintas.
12. Bandeja paginada para todas las solicitudes enviadas, incluyendo estados terminales. Filtros por ID de solicitud, trámite, estado, ID de solicitante y fechas de envío desde/hasta; días interpretados en `America/La_Paz`, extremo superior inclusivo. No se filtra por unidad.
13. Detalle administrativo con carga agrupada de relaciones, requisitos, datos, perfil actual, recepción, etapas, pagos, observaciones, resultado, entrega e historial.

### Compatibilidad con solicitudes anteriores

- Columnas nuevas nullable o con defaults compatibles; no se actualizan solicitudes antiguas al aplicar el SQL.
- Requisitos existentes se interpretan como iniciales y sin exigencia física nueva.
- Solicitudes antiguas sin etapas copiadas continúan sin crear un recorrido artificial.
- Si falta modalidad capturada, administración debe elegirla explícitamente al registrar el resultado; no se toma del catálogo actual por inferencia.
- Las claves/etiquetas y nombre histórico no capturados permanecen nulos. El frontend usa el ID del campo o nombre disponible como referencia, sin inventar valores históricos.
- El perfil académico mostrado en administración es el **perfil actual**. Los requisitos aplicables quedan fijados al enviar y no se recalculan al cambiar ese perfil.

### Configuración antes de recibir nuevos envíos

Se permite preparar un trámite por partes. Para **nuevos envíos**, debe existir modalidad de finalización y al menos una etapa activa: primera inicial, última final y una sola marca de cada tipo. Una única etapa puede ser inicial y final. Los requisitos activos no pueden apuntar a etapas inactivas o de otro trámite. Debe existir costo activo para la gestión del envío y código externo en cada requisito económico aplicable, incluso si el pago corresponde a una etapa posterior.

La configuración incompleta no genera flujos ni costos por defecto: el envío informa qué falta. Los borradores pueden crearse antes del pago.

## 6. Tablas

### Nuevas

| Tabla | Finalidad |
|---|---|
| `solicitud_etapa` | Ejecución de etapas copiadas, actores y fechas |
| `solicitud_historial` | Cronología funcional y visibilidad |
| `solicitud_observacion` | Observaciones y resolución |
| `solicitud_resultado` | Resultado y modalidad final única |
| `solicitud_entrega` | Entrega/recojo final único |

### Ampliadas

| Tabla | Cambio |
|---|---|
| `tramite` | Tiempo estimado, canales, instrucciones, condiciones y modalidad |
| `tramite_etapa` | Visibilidad al solicitante, por defecto falsa |
| `tramite_requisito` | Etapa opcional, presentación física y condición JSONB |
| `solicitud` | Etapa actual, nombre capturado, modalidad, estados e índice de fechas de envío |
| `solicitud_dato` | Clave y etiqueta capturadas |
| `solicitud_requisito` | Etapa operacional, condición capturada y presentación física con actor/fecha |

No se crean tablas paralelas de pagos, tickets, archivos o unidades.

## 7. API

Todas las rutas llevan prefijo `/api`. Se reutilizan `SolicitanteActual`, `PersonalAdministrativoActual` y `AdministradorActual`.

### Nuevas — solicitante (únicamente solicitudes propias)

| Método | Ruta | Uso |
|---|---|---|
| GET | `/solicitudes/{id}/preparacion` | Requisitos aplicables según borrador guardado, sin snapshot |
| GET | `/solicitudes/{id}/seguimiento` | Seguimiento e historial público |
| GET | `/solicitudes/{id}/observaciones` | Observaciones propias |
| POST | `/solicitudes/{id}/cancelar` | `{ "motivo": "..." }` |
| PUT | `/solicitudes/{id}/requisitos/{requisito}/factura` | `{ "numero_factura": "..." }` |

### Nuevas — administración

| Método | Ruta bajo `/admin/solicitudes/{id}` | Uso |
|---|---|---|
| GET | `/historial` | Cronología completa |
| POST | `/iniciar` | Iniciar procesamiento |
| POST | `/avanzar` | `{ "id_solicitud_etapa": <etapa actual> }` |
| POST | `/requisitos/{requisito}/presentacion` | Registrar/repetir presentación física |
| POST | `/observaciones` | Detalle, corrección, canal opcional y referencias opcionales |
| POST | `/observaciones/{observacion}/resolver` | Registrar resolución administrativa |
| POST | `/rechazar` | Motivo obligatorio |
| POST | `/finalizar` | Detalle opcional; modalidad explícita solo si falta snapshot |
| POST | `/entregar` | Receptor, nombre cuando corresponda, documento/detalle opcionales |

Los identificadores `id_solicitud_etapa` y `id_solicitud_requisito` corresponden al snapshot de la solicitud, no a los IDs de plantilla del catálogo.

### Rutas existentes ampliadas

- `POST /solicitudes`, `PATCH /solicitudes/{id}`, `POST /solicitudes/{id}/enviar`: historial, protección de mutaciones y envío con snapshots nuevos.
- `GET /solicitudes/mias`, `GET /solicitudes/{id}`: estados completos, nombre capturado, datos físicos y disponibilidad de registro de factura.
- `GET /admin/solicitudes`, `GET /admin/solicitudes/{id}`: filtros y detalle completo.
- `POST /admin/solicitudes/{id}/recibir`: historial y serialización.
- `POST /admin/solicitudes/{id}/requisitos/{requisito}/verificar` y `/verificar-pago`: reglas de etapa/presentación e historial.
- `GET /tramites` y `/tramites/{id}`: información de atención, pasos visibles, condiciones y costos existentes.
- `POST/PATCH /admin/tramites` y sus rutas de requisitos/etapas: nuevos campos configurables. Se conservan campos y configuraciones económicas por gestión.
- `DELETE /solicitudes/{id}` continúa limitado a borradores propios; no es una cancelación administrativa.
- `GET/PATCH /users/me/perfil-academico` se reutilizan desde preparación.

## 8. Angular

Se reutilizan layout, menú, interceptores, sesión, permisos y `/api` a través del gateway existente. Sin librerías nuevas ni rediseño global.

- `/tramites` y `/tramites/:id`: catálogo público y detalle.
- `/solicitudes/:id/preparar`: datos dinámicos, perfil académico, requisitos aplicables, factura inicial y envío.
- `/mis-solicitudes`: lista paginada y filtro de estado.
- `/solicitudes/:id`: requisitos, seguimiento público, observaciones, cancelación y factura posterior.
- `/admin/solicitudes` y `/admin/solicitudes/:id`: bandeja, filtros y todas las acciones administrativas de M03.
- `/admin/tramites`: configuración M05-F01–F07, campos, requisitos, condiciones de igualdad, etapas y costos. Solo administrador.

La UI deshabilita controles durante acciones y presenta errores del backend. El backend mantiene la autoridad de las reglas aunque alguien omita los controles del cliente. La información pública no incluye nombres de etapas internas ni datos del receptor de una entrega.

## 9. Verificaciones realizadas

Resultados anteriores a la instrucción de utilizar exclusivamente Docker para las verificaciones pendientes. Se obtuvieron con Python 3.14 en un entorno temporal, sin modificar requirements.txt; no equivalen a validaciones en los contenedores del proyecto ni se repitieron localmente tras esa instrucción:

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/m03-check-venv/bin/python backend/scripts/verificar_m03.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend /tmp/m03-check-venv/bin/python -m unittest discover -s backend/tests -p test_gestion_seguimiento.py -v
git diff --check
```

Resultados:

- Compilación en memoria de 146 archivos Python: correcta, sin alterar `.pyc` versionados.
- `configure_mappers`: correcto.
- Comparación estática de columnas de 18 modelos M03 con el SQL maestro; comparación de las cinco tablas nuevas con el manual: correcta.
- Compilación textual de DDL SQLAlchemy para PostgreSQL: correcta. **No es ejecución ni validación del SQL en un servidor.**
- OpenAPI parcial: 26 rutas, 29 operaciones, identificadores únicos. Schemas de detalle/configuración correctos.
- OpenAPI de `admin_tramites` y `admin_unidades` pendiente en un entorno con `python-multipart`, dependencia ya declarada. No se inició auth ni RAG para el preflight.
- 29 pruebas `unittest`: correctas. Repositorios y HTTP sustituidos por dobles en memoria. Incluyen transiciones, condiciones, snapshots, propietarios, físicos, factura posterior, idempotencia, reutilización, timeout y rollback ante fallo del historial.
- `git diff --check`: correcto.
- Referencias locales de imports, plantillas y estilos de los componentes Angular nuevos: correctas; esta inspección no sustituye al compilador Angular.
- Intento `npm run build` desde `frontend`: no pudo iniciar (`npm: command not found`). Sin build ni typecheck Angular confirmado.
- No se ejecutaron pruebas de integración sobre PostgreSQL, prueba de concurrencia real ni navegación de navegador.

### Verificaciones pendientes dentro de Docker

Revisados `docker-compose.yml`, `backend/Dockerfile` y `frontend/Dockerfile`:

- Backend: `python:3.12-slim`, dependencias de `backend/requirements.txt`, directorio `/app` y código montado desde `./backend`.
- Frontend: `node:24-alpine`, dependencias de `package.json`, código montado desde `./frontend` y volumen separado para `/app/node_modules`.
- `backend` depende de PostgreSQL y la mock API; `frontend` depende del backend. No usar `docker compose up` para estas verificaciones previas al SQL.
- Contexto activo: `desktop-linux`; daemon inaccesible por socket inexistente. Configuración Compose validada estáticamente con `docker compose config --quiet`.

Desde la raíz, cuando los contenedores existentes estén disponibles:

```sh
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 backend python scripts/verificar_m03.py
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 backend python -m unittest discover -s tests -p test_gestion_seguimiento.py -v
docker compose exec -T frontend npm run build
```

Si están detenidos pero sus imágenes ya existen, se pueden usar procesos efímeros de esos mismos servicios, sin arrancar dependencias, sin construir imágenes y sustituyendo sus comandos de servidor:

```sh
docker compose run --rm --no-deps --no-build -T -e PYTHONDONTWRITEBYTECODE=1 backend python scripts/verificar_m03.py
docker compose run --rm --no-deps --no-build -T -e PYTHONDONTWRITEBYTECODE=1 backend python -m unittest discover -s tests -p test_gestion_seguimiento.py -v
docker compose run --rm --no-deps --no-build -T frontend npm run build
```

Estos comandos no ejecutan endpoints ni aplican SQL. El preflight bloquea conexiones a bases de datos y las pruebas sustituyen repositorios y HTTP por dobles en memoria. Si faltan imágenes o dependencias dentro de ellas, debe reportarse esa limitación y revisar el entorno Docker; no recurrir a instalaciones locales. No se ejecutó ninguno de estos comandos de validación con el daemon inaccesible.

No se agregaron frameworks de pruebas ni dependencias al proyecto. No se instalaron paquetes adicionales ni se reutilizó el entorno temporal en esta continuación.

## 10. Aplicación manual y aceptación funcional

1. Ejecutar una sola vez en pgAdmin `backend/sql/manual/gestion_seguimiento_fases_4_5_6.sql`, sobre la base que ya contiene Fases 1–3. No ejecutar el maestro encima de esa base.
2. Confirmar que la transacción termina y revisar el SELECT opcional del archivo. Si el esquema real difiere de Fases 1–3, revisar el error antes de intentar adaptar o repetir el script.
3. Completar preflight/OpenAPI, pruebas y build Angular mediante Docker Compose; después de aplicar el SQL, reiniciar backend/frontend con el código actualizado.
4. Mantener la mock API HTTP independiente. Comprobar `PAGO_API_BASE_URL`, `PAGO_API_VALIDAR_PATH`, `PAGO_API_TIMEOUT` y `PAGO_API_TOKEN`. Si la mock exige token, debe coincidir con el configurado en ella.
5. Acceder mediante el gateway existente para conservar el enrutamiento `/api`.
6. Configurar casos de prueba en un entorno de desarrollo, con usuarios/roles existentes; no se insertaron personas ni flujos de producción. Usar códigos, montos, monedas y facturas que realmente existan en la mock o entorno externo elegido.

### Escenarios mínimos

| Escenario | Recorrido y comprobaciones |
|---|---|
| Pago inicial + entrega | Crear borrador antes de pagar; sin factura obligatoria el envío debe fallar; registrar factura y enviar; recibir; si es físico, bloquear acreditación hasta presentación; verificar por API; iniciar y completar etapas; registrar resultado; comprobar `lista_para_entrega`; registrar una entrega y finalizar. Repetir entrega debe fallar. |
| Pago en etapa posterior | Configurar requisito económico en una etapa posterior. Enviar sin esa factura debe funcionar; no se permite registrarla antes de su etapa. Llegar a ella, registrar factura, verificar por la misma API y avanzar. Sin acreditación, el avance debe fallar. |
| Observación | Registrar durante revisión o etapa actual; comprobar que estado/etapa no se mueven y que bloquea inicio/avance/finalización. Solicitante ve qué corregir. Resolver administrativamente y continuar desde la misma etapa. |
| Finalización sin entrega | Probar `resultado_registrado` y `externo`: tras todos los requisitos/etapas y sin observaciones, registrar resultado debe finalizar. El endpoint de entrega debe rechazar la operación. |
| Cancelación y rechazo | Cancelar borrador o pendiente sin factura; bloquear con factura o después de recepción. Rechazar con motivo en un estado permitido; no admitir acciones operativas posteriores. |
| Condiciones y snapshots | Probar condición verdadera/falsa y fuente incompleta. Cambiar catálogo/perfil después del envío y verificar que no cambian etapas, requisitos aplicables, costos ni modalidad capturados. |
| Históricos | Abrir una solicitud anterior sin snapshots nuevos. Procesar sin fabricar etapas; elegir modalidad explícita al finalizar. Comprobar que no aparecen eventos retroactivos. |
| Acceso y concurrencia | Otro solicitante no puede leer/modificar la solicitud. Personal administrativo puede gestionar, pero no configurar catálogo. Enviar simultáneamente dos avances, resultados o entregas no debe duplicarlos. Verificar la misma factura para dos solicitudes concurrentes solo debe acreditar una. |
| Errores de pagos | Factura inexistente, concepto/monto/moneda incorrectos, impaga o reutilizada: no acreditar. Timeout/error: intento `error`, sin crédito. Repetir éxito sobre el mismo requisito: devolver resultado previo. |

### Patrones institucionales soportados por configuración

| Patrón del requerimiento | Configuración necesaria, sin implementación específica por nombre |
|---|---|
| Diploma/Título, certificados, legalizaciones | Pago inicial y requisitos físicos; etapas confirmadas; modalidad entrega |
| Certificado supletorio | Campo motivo y requisito condicionado por igualdad; modalidad confirmada |
| Apostilla | Etapa lineal de gestión/confirmación externa operada por administración; entrega si corresponde; sin integración externa |
| Cambio de sede | Requisitos iniciales y revisión; resultado sin entrega si corresponde |
| Traspaso | Requisito económico ligado a etapa posterior a revisión/aceptación |
| Movilidad estudiantil | Varias etapas lineales configurables con unidades opcionales |

Estos patrones no se sembraron en la base ni se codificaron como reglas especiales.

## 11. Decisiones institucionales y deuda que permanecen

- Deben confirmarse nombres y orden de etapas, unidades opcionales, visibilidad pública, requisitos físicos/condicionales, costos por gestión, códigos externos, canales, tiempos y modalidades.
- No se implementa la regla de año 2015 ni recorridos deducidos a partir de nombres/personas.
- No hay acceso por unidad, automatización externa, documentos, cobro, reembolso, firmas, notificaciones completas ni M06.
- El SQL real y las carreras concurrentes deben probarse después de aplicación manual; las pruebas en memoria no los sustituyen.
- Build y navegación Angular pendientes por las limitaciones descritas. No se afirma que la UI fue ejecutada.
- Se conservaron los cambios preexistentes en `.pyc` versionados. Su limpieza y la fijación/reproducibilidad general de dependencias quedan fuera del desarrollo M03.

## 12. Inventario de archivos

### Creados

- `backend/app/api/routes/gestion_seguimiento/seguimiento.py`
- `backend/app/models/gestion_seguimiento/solicitud_entrega.py`
- `backend/app/models/gestion_seguimiento/solicitud_etapa.py`
- `backend/app/models/gestion_seguimiento/solicitud_historial.py`
- `backend/app/models/gestion_seguimiento/solicitud_observacion.py`
- `backend/app/models/gestion_seguimiento/solicitud_resultado.py`
- `backend/app/repositories/gestion_seguimiento/seguimiento_repository.py`
- `backend/app/schemas/gestion_seguimiento/seguimiento.py`
- `backend/app/services/gestion_seguimiento/configuracion_flujo_service.py`
- `backend/app/services/gestion_seguimiento/seguimiento_service.py`
- `backend/scripts/verificar_m03.py`
- `backend/sql/manual/gestion_seguimiento_fases_4_5_6.sql`
- `backend/tests/test_gestion_seguimiento.py`
- `docs/m03-fases-4-5-6.md`
- `frontend/src/app/features/gestion-seguimiento/catalogo.component.html`
- `frontend/src/app/features/gestion-seguimiento/catalogo.component.ts`
- `frontend/src/app/features/gestion-seguimiento/configuracion.component.html`
- `frontend/src/app/features/gestion-seguimiento/configuracion.component.ts`
- `frontend/src/app/features/gestion-seguimiento/gestion.models.ts`
- `frontend/src/app/features/gestion-seguimiento/gestion.scss`
- `frontend/src/app/features/gestion-seguimiento/gestion.service.ts`
- `frontend/src/app/features/gestion-seguimiento/preparar.component.html`
- `frontend/src/app/features/gestion-seguimiento/preparar.component.ts`
- `frontend/src/app/features/gestion-seguimiento/solicitud-detalle.component.html`
- `frontend/src/app/features/gestion-seguimiento/solicitud-detalle.component.ts`
- `frontend/src/app/features/gestion-seguimiento/solicitudes-lista.component.html`
- `frontend/src/app/features/gestion-seguimiento/solicitudes-lista.component.ts`

### Modificados

- `backend/app/api/router.py`
- `backend/app/api/routes/gestion_seguimiento/admin_solicitudes.py`
- `backend/app/main.py`
- `backend/app/models/gestion_seguimiento/__init__.py`
- `backend/app/models/gestion_seguimiento/solicitud.py`
- `backend/app/models/gestion_seguimiento/solicitud_dato.py`
- `backend/app/models/gestion_seguimiento/solicitud_requisito.py`
- `backend/app/models/gestion_seguimiento/tramite.py`
- `backend/app/models/gestion_seguimiento/tramite_etapa.py`
- `backend/app/models/gestion_seguimiento/tramite_requisito.py`
- `backend/app/repositories/gestion_seguimiento/solicitud_administrativa_repository.py`
- `backend/app/schemas/gestion_seguimiento/solicitud.py`
- `backend/app/schemas/gestion_seguimiento/solicitud_administrativa.py`
- `backend/app/schemas/gestion_seguimiento/tramite.py`
- `backend/app/schemas/gestion_seguimiento/tramite_etapa.py`
- `backend/app/schemas/gestion_seguimiento/tramite_requisito.py`
- `backend/app/services/gestion_seguimiento/pago_verificacion_service.py`
- `backend/app/services/gestion_seguimiento/solicitud_administrativa_service.py`
- `backend/app/services/gestion_seguimiento/solicitud_service.py`
- `backend/app/services/gestion_seguimiento/tramite_service.py`
- `backend/database.sql`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/core/config/sidebar-menu.config.ts`

Los binarios `.pyc` ya figuraban modificados al iniciar la tarea y no pertenecen a esta implementación.

## 13. Contraste final con los criterios de aceptación

**CUMPLIDO significa implementado y contrastado por inspección del código, no aceptación funcional ejecutada.** La aceptación integral de M03 permanece bloqueada por las verificaciones indicadas al final. No se ejecutó SQL ni se instalaron dependencias locales.

En esta continuación se corrigió únicamente `configuracion.component.ts`: una selección fallida conserva el ID del formulario que sigue visible; después de guardar, lista y detalle se recargan juntos sin habilitar controles prematuramente. El ID de un trámite recién creado se conserva aunque falle la recarga, para evitar repetir el alta. RxJS ya era una dependencia del proyecto. No se reescribieron servicios ni esquemas que ya cumplían los criterios.

Referencias abreviadas: los servicios están en `backend/app/services/gestion_seguimiento/`; los componentes, en `frontend/src/app/features/gestion-seguimiento/`. Las rutas y permisos están documentados en las secciones 7 y 8.

| ID | Criterio original | Estado | Evidencia de implementación |
|---|---|---|---|
| S01 | Consulta trámites | CUMPLIDO | `tramite_service.obtener_catalogo_publicado`; `catalogo.component` |
| S02 | Ve información/requisitos | CUMPLIDO | `obtener_tramite_catalogo_publico`; detalle del catálogo |
| S03 | Crea antes de pagar | CUMPLIDO | `solicitud_service.crear_solicitud`; creación de borrador desde catálogo |
| S04 | Completa información | CUMPLIDO | `actualizar_solicitud`; formulario dinámico y perfil en `preparar.component` |
| S05 | Registra pago inicial | CUMPLIDO | `_normalizar_facturas_envio`; factura inicial en preparación; pago externo |
| S06 | Envía | CUMPLIDO | `enviar_solicitud`; validación y snapshots al enviar |
| S07 | Ve solicitudes | CUMPLIDO | `listar_mis_solicitudes`; `solicitudes-lista.component` |
| S08 | Seguimiento/historial | CUMPLIDO | `seguimiento_service.consultar_seguimiento`; `solicitud-detalle.component` |
| S09 | Observaciones | CUMPLIDO | Consulta propia y sección de observaciones en detalle |
| S10 | Registra factura posterior | CUMPLIDO | `registrar_factura`; edición habilitada según etapa en detalle |
| S11 | Cancela cuando corresponde | CUMPLIDO | `cancelar`; controles de propiedad, estado y facturas; acción en detalle |
| A01 | Bandeja/filtros | CUMPLIDO | `solicitud_administrativa_service.listar_bandeja_administrativa`; lista administrativa |
| A02 | Detalle | CUMPLIDO | `obtener_detalle_administrativo`; detalle administrativo Angular |
| A03 | Recepción | CUMPLIDO | `recibir_solicitud`; acción de recepción |
| A04 | Recepción física | CUMPLIDO | `registrar_presentacion`; actor/fecha separados de acreditación |
| A05 | Verificación | CUMPLIDO | `verificar_requisito_manual`; acción por requisito no económico |
| A06 | Pagos vía API | CUMPLIDO | `pago_verificacion_service.verificar_pago_requisito`; cliente HTTP existente |
| A07 | Iniciar proceso | CUMPLIDO | `iniciar_procesamiento`; acción administrativa |
| A08 | Avanzar etapas | CUMPLIDO | `avanzar_etapa`; ID esperado de etapa y bloqueo de solicitud |
| A09 | Bloqueo por requisito | CUMPLIDO | `exigir_requisitos`; validación física y económica |
| A10 | Bloqueo por observación | CUMPLIDO | `exigir_sin_observaciones`; inicio, avance y resultado |
| A11 | Observaciones | CUMPLIDO | `crear_observacion`; formulario administrativo |
| A12 | Resolver | CUMPLIDO | `resolver_observacion`; acción administrativa |
| A13 | Rechazar | CUMPLIDO | `rechazar`; motivo y estados permitidos |
| A14 | Resultado | CUMPLIDO | `registrar_resultado`; resultado único y modalidad capturada |
| A15 | Lista entrega | CUMPLIDO | Estado `lista_para_entrega`; filtro de bandeja y detalle |
| A16 | Una sola entrega | CUMPLIDO | `registrar_entrega`; bloqueo, estado y unicidad por solicitud |
| A17 | Finalizar | CUMPLIDO | Resultado o entrega según modalidad; acción en detalle |
| A18 | Historial completo | CUMPLIDO | `evento`, consulta administrativa de historial y detalle |
| C01 | Requisitos iniciales | CUMPLIDO | Requisito sin etapa; `tramite_service`; `configuracion.component` |
| C02 | Requisitos por etapa | CUMPLIDO | Asociación de plantilla y snapshot; validación de pertenencia |
| C03 | Económicos | CUMPLIDO | Configuración económica por gestión, monto, moneda y código externo |
| C04 | Físicos | CUMPLIDO | `requiere_presentacion_fisica` en configuración, snapshot y acciones |
| C05 | Condición simple | CUMPLIDO | `configuracion_flujo_service.validar_condicion` y `requisitos_aplicables`; igualdad tipada |
| C06 | Etapas lineales | CUMPLIDO | `validar_flujo_envio`; ejecución por orden y una etapa en curso |
| C07 | Unidad opcional | CUMPLIDO | `id_unidad` nullable; validación de unidad y formulario de etapa |
| C08 | Información pública | CUMPLIDO | Información de atención y visibilidad de etapas; catálogo y configuración |
| C09 | Forma finalización | CUMPLIDO | Modalidad configurable, capturada y aplicada al resultado |
| H01 | Catálogo no modifica snapshots existentes | CUMPLIDO | Copias en `enviar_solicitud`; acciones operativas usan copias |
| H02 | Solicitudes antiguas compatibles | CUMPLIDO | Campos nullable/defaults; sin etapas artificiales; modalidad explícita si no existe snapshot |
| H03 | Sin backfill artificial | CUMPLIDO | Manual SQL sin actualizaciones de datos ni inserciones históricas |

### Verificaciones de esta continuación y pendientes

| Verificación | Estado | Resultado o dependencia |
|---|---|---|
| Conservación del esquema Fases 1–3 | CUMPLIDO | Comparación textual de `git show HEAD:backend/database.sql` más el manual contra el maestro: 27 tablas con columnas, tipos, defaults y constraints coincidentes; índices, triggers, funciones y roles coincidentes. Se excluyeron consultas de comprobación y semillas de personas deliberadamente eliminadas. No se ejecutó SQL. |
| Coherencia SQL/ORM | CUMPLIDO | Inspección y comparación previa de columnas de 18 modelos y cinco tablas nuevas documentada en sección 9; modelos sin cambios en esta continuación. La comprobación dinámica en Docker sigue bloqueada. |
| Sintaxis Python | CUMPLIDO | `python3 -B` existente: `compile()` en memoria de 146 fuentes, sin importarlas ni generar `.pyc`, usando solo biblioteca estándar. No equivale a ejecución del backend. |
| Configuración Compose | CUMPLIDO | `docker compose config --quiet`: salida 0. |
| Comprobación del diff | CUMPLIDO | `git diff --check`: salida 0; solo cubre archivos rastreados. |
| Preflight completo, mappers y pruebas backend en Docker | BLOQUEADO | `docker compose ps` falla por socket inexistente del daemon; no se ejecutaron ni se instalaron dependencias alternativas. |
| Build Angular tras la corrección | BLOQUEADO | Mismo bloqueo de Docker; pendiente `npm run build` dentro del servicio frontend. |
| Prueba de selección/recarga Angular | BLOQUEADO | Probar fallo al seleccionar otro trámite, recargas con latencias distintas y alta exitosa seguida de error al recargar; requiere entorno Angular disponible. |
| Escenarios funcionales e integridad/concurrencia real | BLOQUEADO | Requieren aplicación manual del SQL por el usuario y entorno disponible. Se mantiene la prohibición de tocar PostgreSQL. |
| Configuración institucional efectiva | PENDIENTE | Confirmar datos reales de etapas, unidades, requisitos, costos y modalidades. No se inventaron ni sembraron procesos. |

No queda identificada una funcionalidad ausente de los 41 criterios. Esto no permite declarar M03 aceptado en ejecución hasta completar build, preflight y escenarios funcionales. Los pasos y comandos pendientes permanecen en las secciones 9 y 10.
