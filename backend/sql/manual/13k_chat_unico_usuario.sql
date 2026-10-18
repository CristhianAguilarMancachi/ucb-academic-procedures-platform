BEGIN;

ALTER TABLE public.chat_session
    ADD COLUMN IF NOT EXISTS id_usuario BIGINT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.chat_session'::regclass
          AND conname = 'fk_chat_session_usuario'
    ) THEN
        ALTER TABLE public.chat_session
        ADD CONSTRAINT fk_chat_session_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES public.usuario(id_usuario)
        ON DELETE CASCADE;
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS
    uq_chat_session_usuario
ON public.chat_session (id_usuario)
WHERE id_usuario IS NOT NULL;

COMMIT;
