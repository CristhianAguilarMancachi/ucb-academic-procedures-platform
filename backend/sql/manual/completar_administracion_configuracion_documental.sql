-- Aplicación MANUAL. No ha sido ejecutado por la implementación.
-- Requiere el esquema documental existente (version_documento / pgvector 512).
-- No crea otra estructura documental, no reingesta ni modifica PDFs o embeddings.
-- Aplicar antes de desplegar el backend que lee estas dos columnas.
BEGIN;

ALTER TABLE version_documento
    ADD COLUMN IF NOT EXISTS vigente_desde DATE,
    ADD COLUMN IF NOT EXISTS vigente_hasta DATE;

-- Sin backfill: las versiones previas conservan NULL. El backend utiliza
-- fecha_version como inicio efectivo hasta definir una vigencia explícita.
-- Toda nueva carga y edición de vigencia exige vigente_desde en la API.
DO $vigencia$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'version_documento'::regclass
          AND conname = 'ck_version_documento_vigencia'
    ) THEN
        ALTER TABLE version_documento
            ADD CONSTRAINT ck_version_documento_vigencia CHECK (
                vigente_hasta IS NULL
                OR (vigente_desde IS NOT NULL AND vigente_hasta >= vigente_desde)
            );
    END IF;
END;
$vigencia$;

COMMIT;
