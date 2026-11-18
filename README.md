# Sistema de Gestión y Seguimiento de Trámites Académicos

Plataforma web para la gestión y seguimiento de trámites académicos, desarrollada en el contexto de la Universidad Católica Boliviana "San Pablo" — Sede La Paz, como parte de un Trabajo Dirigido de Ingeniería de Sistemas.

La solución permite registrar solicitudes, consultar su estado y realizar operaciones de atención administrativa. Incorpora además un módulo informativo basado en Retrieval-Augmented Generation (RAG) para responder consultas sobre documentación institucional.

El módulo RAG tiene carácter informativo: no ejecuta trámites, modifica estados ni toma decisiones administrativas.

## 1. Funcionalidades principales

La plataforma se organiza en los siguientes módulos:

- Gestión de acceso, autenticación y cuentas de usuario.
- Consulta del catálogo de trámites académicos.
- Registro y seguimiento de solicitudes.
- Atención administrativa, requisitos, observaciones y resultados.
- Administración de usuarios y roles.
- Configuración de trámites y sus condiciones de atención.
- Gestión de documentación institucional y sus versiones.
- Consultas mediante el módulo informativo RAG.
- Analítica e indicadores de utilización.

El sistema contempla cuatro perfiles de uso: usuario del módulo informativo, solicitante, personal administrativo y administrador.

## 2. Arquitectura tecnológica

### Frontend

- Angular 17.
- TypeScript.
- Interfaces web adaptables a diferentes tamaños de pantalla.

### Backend

- Python.
- FastAPI.
- Uvicorn.
- SQLAlchemy para acceso a datos.

### Base de datos

- PostgreSQL.
- Extensión pgvector para almacenamiento y consulta de representaciones vectoriales.

La plataforma utiliza PostgreSQL para mantener la información de usuarios, trámites, solicitudes, requisitos, observaciones, historial, documentos institucionales y datos del módulo RAG.

### Módulo RAG

- PyMuPDF para extracción de texto de documentos PDF.
- Tesseract OCR cuando se requiere reconocimiento de texto.
- Jina AI para generar embeddings.
- PostgreSQL con pgvector para recuperación de fragmentos documentales.
- Groq para la generación de respuestas mediante un modelo de lenguaje.

Las respuestas se generan a partir de información recuperada desde los documentos institucionales habilitados. El módulo conserva referencias a las fuentes utilizadas.

### Servicios complementarios

- Google Identity Services para autenticación mediante Google.
- Brevo para comunicaciones por correo electrónico.
- API simulada para verificar requisitos económicos.

La plataforma no procesa pagos reales ni sustituye la presentación presencial de documentos cuando el trámite la requiere.

## 3. Organización del repositorio

El proyecto está distribuido principalmente en:

- `backend/`: API, lógica de negocio, modelos, repositorios, servicios, pruebas y configuración del backend.
- `frontend/`: aplicación web desarrollada con Angular.
- `docker-compose.yml`: configuración de los servicios necesarios para ejecutar el entorno local.
- `README.md`: descripción general e instrucciones principales.

La lógica del backend se organiza por responsabilidades, incluyendo autenticación, usuarios, gestión y seguimiento de trámites y módulo informativo RAG.

## 4. Requisitos de ejecución

Para ejecutar la plataforma en el entorno local se requiere:

- Git.
- Docker.
- Docker Compose.
- Acceso a los servicios externos utilizados por el proyecto cuando corresponda.
- Credenciales y variables de entorno configuradas.

El frontend y el backend se ejecutan mediante contenedores. No es necesario instalar las dependencias de Angular globalmente para utilizar el entorno Docker del proyecto.

## 5. Configuración del entorno

Clonar el repositorio:

```bash
git clone <URL_DEL_REPOSITORIO>
cd ucb-academic-procedures-platform
```

Preparar la configuración del backend utilizando como referencia:

```text
backend/.env.example
```

Crear el archivo:

```text
backend/.env
```

Completar las variables requeridas por la configuración actual, incluyendo las credenciales de base de datos y los servicios externos habilitados.

Las claves de acceso de Jina AI, Groq y otros proveedores deben configurarse conforme a los nombres de variables definidos en el backend y en el archivo de ejemplo.

No incluir valores reales de contraseñas, tokens o claves de API en el repositorio.

### Base de datos

La aplicación requiere una base de datos PostgreSQL con las estructuras utilizadas por sus módulos y la extensión pgvector habilitada.

El repositorio contiene una referencia del esquema en `backend/database.sql`.

La preparación inicial de una base de datos debe realizarse conforme al entorno correspondiente. No se deben ejecutar scripts de creación sobre una base existente sin verificar previamente su estado y compatibilidad.

## 6. Ejecución local

Desde la raíz del proyecto:

```bash
docker compose build
docker compose up -d
```

Consultar los servicios:

```bash
docker compose ps
```

Revisar los registros:

```bash
docker compose logs --tail=100
```

Acceder a la aplicación mediante:

```text
http://localhost:8080
```

La configuración de Docker Compose incluye los componentes necesarios para el entorno local y su comunicación a través del gateway.

Para detener los servicios:

```bash
docker compose down
```

No utilizar opciones de eliminación de volúmenes si se desea conservar la información almacenada localmente.

## 7. Pruebas del backend

El repositorio contiene pruebas automatizadas de las funciones principales del sistema.

Las pruebas cubren diferentes aspectos de la plataforma, entre ellos:

- Autenticación y control de acceso.
- Gestión y seguimiento de solicitudes.
- Operaciones administrativas.
- Reglas de negocio y validaciones.
- Integración entre componentes.
- Procesamiento documental y recuperación de información del módulo RAG.

Algunas pruebas utilizan simulaciones de dependencias externas. Estas pruebas deben distinguirse de las comprobaciones funcionales realizadas directamente sobre la aplicación y la base de datos.

## 8. Despliegue

La arquitectura del proyecto contempla los siguientes servicios:

- Cloudflare Pages para el frontend.
- Render para el backend.
- Neon para PostgreSQL.

El funcionamiento del módulo RAG depende además de la disponibilidad de Jina AI y Groq.

Las configuraciones y credenciales de producción deben mantenerse separadas de los archivos públicos del repositorio.

## 9. Consideraciones del prototipo

El sistema está desarrollado para el alcance académico e institucional definido en el Trabajo Dirigido.

Se consideran las siguientes restricciones:

- Los pagos no son procesados directamente por la plataforma.
- La verificación económica utiliza una API simulada.
- Los requisitos documentales físicos se presentan mediante los canales institucionales correspondientes.
- El módulo RAG proporciona información, pero no autoriza ni ejecuta procedimientos administrativos.
- La información recuperada depende de los documentos incorporados, habilitados y vigentes.
- El historial de solicitudes conserva las acciones relevantes de su atención.

## 10. Estado del proyecto

Prototipo funcional desarrollado y sometido a pruebas unitarias, de integración, funcionales, de rendimiento y de usabilidad dentro del alcance del Trabajo Dirigido.
