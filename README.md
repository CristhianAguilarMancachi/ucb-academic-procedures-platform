# ucb-academic-procedures-platform

Sistema para la gestión y seguimiento de trámites académicos basado en flujos de procesos administrativos, con un módulo informativo RAG para la consulta de requisitos, procedimientos y normativa institucional.

El proyecto está orientado al contexto de la Universidad Católica Boliviana “San Pablo” – Sede La Paz y se desarrolla como parte de un trabajo dirigido de Ingeniería de Sistemas. El módulo RAG tiene un carácter informativo y servirá como apoyo para consultar documentación oficial, sin intervenir directamente en la ejecución formal de los trámites. :contentReference[oaicite:5]{index=5} :contentReference[oaicite:6]{index=6}

## Stack actual

- Python
- FastAPI
- Angular
- PostgreSQL + pgvector
- Embeddings locales: Sentence Transformers, `paraphrase-multilingual-MiniLM-L12-v2`, dimensión 384
- Generación textual: Groq API, `openai/gpt-oss-120b`
- PDF: PyMuPDF; OCR: Tesseract, pdf2image y Pillow

## Configuración y ejecución

1. Clonar el repositorio y preparar `backend/.env` a partir de `backend/.env.example`.
2. Completar la configuración del backend y establecer `GROQ_API_KEY` únicamente en ese archivo ignorado por Git y por la construcción Docker.
3. Ejecutar `docker compose build` y `docker compose up -d`.
4. Acceder a la aplicación mediante `http://localhost:8080`.

Groq utiliza Chat Completions mediante HTTPS, con timeout de 30 segundos y hasta dos reintentos del SDK. El backend recibe las variables mediante el `env_file` existente. No requiere servidor ni modelo generativo local. El hosting debe permitir salida HTTPS al proveedor.

La clasificación usa primero reglas locales; su fallback, la reformulación con historial y la generación comparten un cliente Groq síncrono. `/health` y `/ready` no realizan llamadas al proveedor. Los errores del proveedor devuelven HTTP 503 sin guardar respuestas vacías.

Se conserva `POST /api/rag/query`, con `session_id`, respuesta y fuentes. Documentos, chunks, recuperación, embeddings e historial mantienen su infraestructura existente. Esta migración no inicializa ni modifica el esquema de PostgreSQL: una instalación nueva necesita el aprovisionamiento de base de datos del proyecto; sobre una existente no se deben ejecutar scripts de creación ni reingestar documentos para cambiar el proveedor.

## Estado

En desarrollo.
