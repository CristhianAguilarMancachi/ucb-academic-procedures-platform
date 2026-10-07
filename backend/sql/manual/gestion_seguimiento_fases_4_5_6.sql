-- M03: ampliación de Fases 1–3 a Fases 4–6.
-- Ejecutar UNA VEZ, manualmente en pgAdmin, sobre el esquema de database.sql Fases 1–3.
-- No ejecutar database.sql sobre una base existente. No hay seeds ni backfill.
-- Los NULL distinguen información no capturada en solicitudes anteriores.
-- En proceso conserva id_etapa_actual, incluso al completar la última etapa,
-- hasta registrar resultado. Históricos sin etapas finalizan desde revisión.
-- La base de partida debe corresponder a F1–3: si hubiera filas en_proceso
-- introducidas por otros medios sin etapa, la nueva CHECK rechazará el script.
-- No se corrigen ni inventan datos históricos automáticamente.
BEGIN;

ALTER TABLE tramite
    ADD COLUMN tiempo_estimado TEXT,
    ADD COLUMN canales_atencion TEXT,
    ADD COLUMN instrucciones TEXT,
    ADD COLUMN condiciones TEXT,
    ADD COLUMN tipo_finalizacion VARCHAR(30),
    ADD CONSTRAINT ck_tramite_tipo_finalizacion CHECK
        (tipo_finalizacion IN ('entrega', 'resultado_registrado', 'externo'));
ALTER TABLE tramite_etapa
    ADD COLUMN visible_solicitante BOOLEAN NOT NULL DEFAULT FALSE,
    ADD CONSTRAINT uq_tramite_etapa_pertenencia UNIQUE (id_tramite, id_etapa);
ALTER TABLE tramite_requisito
    ADD COLUMN id_etapa BIGINT,
    ADD CONSTRAINT fk_tramite_requisito_etapa FOREIGN KEY (id_tramite, id_etapa)
        REFERENCES tramite_etapa(id_tramite, id_etapa) ON DELETE RESTRICT,
    ADD COLUMN requiere_presentacion_fisica BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN condicion JSONB,
    ADD CONSTRAINT ck_tramite_requisito_condicion CHECK
        (condicion IS NULL OR (jsonb_typeof(condicion) = 'object'
            AND condicion->>'operador' = 'igual'
            AND condicion->>'origen' IN ('solicitud_dato', 'perfil_academico')));
CREATE INDEX idx_tramite_requisito_etapa ON tramite_requisito(id_etapa);

ALTER TABLE solicitud
    ADD COLUMN id_etapa_actual BIGINT,
    ADD CONSTRAINT ck_solicitud_proceso_etapa CHECK (estado <> 'en_proceso' OR id_etapa_actual IS NOT NULL),
    ADD COLUMN nombre_tramite_snapshot VARCHAR(200),
    ADD COLUMN tipo_finalizacion VARCHAR(30),
    ADD CONSTRAINT ck_solicitud_tipo_finalizacion CHECK
        (tipo_finalizacion IN ('entrega', 'resultado_registrado', 'externo')),
    DROP CONSTRAINT ck_solicitud_estado,
    DROP CONSTRAINT ck_solicitud_fecha_envio;
ALTER TABLE solicitud
    ADD CONSTRAINT ck_solicitud_estado CHECK (estado IN (
        'borrador', 'pendiente_recepcion', 'en_revision', 'en_proceso',
        'lista_para_entrega', 'finalizada', 'cancelada', 'rechazada')),
    ADD CONSTRAINT ck_solicitud_fecha_envio CHECK (
        (estado = 'borrador' AND fecha_envio IS NULL)
        OR estado = 'cancelada'
        OR (estado NOT IN ('borrador', 'cancelada') AND fecha_envio IS NOT NULL));
ALTER TABLE solicitud_dato
    ADD COLUMN clave_snapshot VARCHAR(100),
    ADD COLUMN etiqueta_snapshot VARCHAR(200);

CREATE TABLE solicitud_etapa (
    id_solicitud_etapa BIGSERIAL PRIMARY KEY,
    id_solicitud BIGINT NOT NULL REFERENCES solicitud(id_solicitud) ON DELETE CASCADE,
    id_etapa_origen BIGINT REFERENCES tramite_etapa(id_etapa) ON DELETE RESTRICT,
    id_unidad BIGINT REFERENCES unidad_administrativa(id_unidad) ON DELETE RESTRICT,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    orden INTEGER NOT NULL CHECK (orden > 0),
    es_inicial BOOLEAN NOT NULL,
    es_final BOOLEAN NOT NULL,
    visible_solicitante BOOLEAN NOT NULL DEFAULT FALSE,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    id_usuario_inicio BIGINT REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    id_usuario_finalizacion BIGINT REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    fecha_inicio TIMESTAMPTZ,
    fecha_finalizacion TIMESTAMPTZ,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_solicitud_etapa_orden UNIQUE (id_solicitud, orden),
    CONSTRAINT uq_solicitud_etapa_origen UNIQUE (id_solicitud, id_etapa_origen),
    CONSTRAINT uq_solicitud_etapa_pertenencia UNIQUE (id_solicitud, id_solicitud_etapa),
    CONSTRAINT ck_solicitud_etapa_estado CHECK (estado IN ('pendiente', 'en_curso', 'completada')),
    CONSTRAINT ck_solicitud_etapa_fechas CHECK (
        (estado = 'pendiente' AND fecha_inicio IS NULL AND fecha_finalizacion IS NULL
            AND id_usuario_inicio IS NULL AND id_usuario_finalizacion IS NULL)
        OR (estado = 'en_curso' AND fecha_inicio IS NOT NULL AND id_usuario_inicio IS NOT NULL
            AND fecha_finalizacion IS NULL AND id_usuario_finalizacion IS NULL)
        OR (estado = 'completada' AND fecha_inicio IS NOT NULL AND fecha_finalizacion IS NOT NULL
            AND id_usuario_inicio IS NOT NULL AND id_usuario_finalizacion IS NOT NULL
            AND fecha_finalizacion >= fecha_inicio)),
    CONSTRAINT ck_solicitud_etapa_inicio CHECK (fecha_inicio IS NULL OR fecha_inicio >= fecha_creacion)
);
CREATE UNIQUE INDEX uq_solicitud_etapa_inicial ON solicitud_etapa(id_solicitud) WHERE es_inicial = TRUE;
CREATE UNIQUE INDEX uq_solicitud_etapa_final ON solicitud_etapa(id_solicitud) WHERE es_final = TRUE;
CREATE UNIQUE INDEX uq_solicitud_etapa_en_curso ON solicitud_etapa(id_solicitud) WHERE estado = 'en_curso';
CREATE TRIGGER trg_solicitud_etapa_fecha_actualizacion BEFORE UPDATE ON solicitud_etapa
    FOR EACH ROW EXECUTE FUNCTION actualizar_fecha_actualizacion();
-- FK compuesta: la etapa actual debe pertenecer a la misma solicitud.
ALTER TABLE solicitud ADD CONSTRAINT fk_solicitud_etapa_actual
    FOREIGN KEY (id_solicitud, id_etapa_actual)
    REFERENCES solicitud_etapa(id_solicitud, id_solicitud_etapa);
CREATE INDEX idx_solicitud_etapa_actual ON solicitud(id_etapa_actual);
CREATE INDEX idx_solicitud_fecha_envio ON solicitud(fecha_envio, id_solicitud)
    WHERE fecha_envio IS NOT NULL;

ALTER TABLE solicitud_requisito
    ADD COLUMN id_solicitud_etapa BIGINT,
    ADD COLUMN requiere_presentacion_fisica BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN presentado BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN fecha_presentacion TIMESTAMPTZ,
    ADD COLUMN id_usuario_presentacion BIGINT REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    ADD COLUMN condicion_snapshot JSONB,
    ADD CONSTRAINT fk_solicitud_requisito_etapa FOREIGN KEY (id_solicitud, id_solicitud_etapa)
        REFERENCES solicitud_etapa(id_solicitud, id_solicitud_etapa),
    ADD CONSTRAINT uq_solicitud_requisito_pertenencia UNIQUE (id_solicitud, id_solicitud_requisito),
    ADD CONSTRAINT ck_solicitud_requisito_presentacion CHECK (
        (NOT presentado AND fecha_presentacion IS NULL AND id_usuario_presentacion IS NULL)
        OR (presentado AND requiere_presentacion_fisica AND fecha_presentacion IS NOT NULL
            AND id_usuario_presentacion IS NOT NULL AND fecha_presentacion >= fecha_creacion));
CREATE INDEX idx_solicitud_requisito_etapa ON solicitud_requisito(id_solicitud_etapa);

CREATE TABLE solicitud_historial (
    id_historial BIGSERIAL PRIMARY KEY,
    id_solicitud BIGINT NOT NULL REFERENCES solicitud(id_solicitud) ON DELETE CASCADE,
    id_usuario_actor BIGINT REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    id_solicitud_etapa BIGINT,
    id_solicitud_requisito BIGINT,
    CONSTRAINT fk_historial_etapa FOREIGN KEY (id_solicitud, id_solicitud_etapa) REFERENCES solicitud_etapa(id_solicitud, id_solicitud_etapa),
    CONSTRAINT fk_historial_requisito FOREIGN KEY (id_solicitud, id_solicitud_requisito) REFERENCES solicitud_requisito(id_solicitud, id_solicitud_requisito),
    evento VARCHAR(80) NOT NULL,
    detalle TEXT NOT NULL,
    visible_solicitante BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_evento TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_solicitud_historial_texto CHECK (length(trim(evento)) > 0 AND length(trim(detalle)) > 0)
);
CREATE INDEX idx_solicitud_historial_cronologia ON solicitud_historial(id_solicitud, fecha_evento, id_historial);

CREATE TABLE solicitud_observacion (
    id_observacion BIGSERIAL PRIMARY KEY,
    id_solicitud BIGINT NOT NULL REFERENCES solicitud(id_solicitud) ON DELETE RESTRICT,
    id_solicitud_etapa BIGINT,
    id_solicitud_requisito BIGINT,
    id_usuario_observador BIGINT NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    detalle TEXT NOT NULL,
    correccion_requerida TEXT NOT NULL,
    canal_subsanacion TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    fecha_observacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_usuario_resolucion BIGINT REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    fecha_resolucion TIMESTAMPTZ,
    CONSTRAINT fk_observacion_etapa FOREIGN KEY (id_solicitud, id_solicitud_etapa)
        REFERENCES solicitud_etapa(id_solicitud, id_solicitud_etapa),
    CONSTRAINT fk_observacion_requisito FOREIGN KEY (id_solicitud, id_solicitud_requisito)
        REFERENCES solicitud_requisito(id_solicitud, id_solicitud_requisito),
    CONSTRAINT ck_observacion_texto CHECK (length(trim(detalle)) > 0 AND length(trim(correccion_requerida)) > 0),
    CONSTRAINT ck_observacion_resolucion CHECK (
        (estado = 'pendiente' AND id_usuario_resolucion IS NULL AND fecha_resolucion IS NULL)
        OR (estado = 'resuelta' AND id_usuario_resolucion IS NOT NULL AND fecha_resolucion IS NOT NULL
            AND fecha_resolucion >= fecha_observacion))
);
CREATE INDEX idx_solicitud_observacion_estado ON solicitud_observacion(id_solicitud, estado);

CREATE TABLE solicitud_resultado (
    id_resultado BIGSERIAL PRIMARY KEY,
    id_solicitud BIGINT NOT NULL UNIQUE REFERENCES solicitud(id_solicitud) ON DELETE RESTRICT,
    tipo_finalizacion VARCHAR(30) NOT NULL CHECK (tipo_finalizacion IN ('entrega', 'resultado_registrado', 'externo')),
    detalle TEXT,
    id_usuario_registro BIGINT NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE solicitud_entrega (
    id_entrega BIGSERIAL PRIMARY KEY,
    id_solicitud BIGINT NOT NULL UNIQUE REFERENCES solicitud(id_solicitud) ON DELETE RESTRICT,
    id_usuario_entrega BIGINT NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    receptor VARCHAR(10) NOT NULL CHECK (receptor IN ('titular', 'tercero')),
    nombre_receptor VARCHAR(200),
    documento_identidad VARCHAR(50),
    detalle TEXT,
    fecha_entrega TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_entrega_receptor CHECK (receptor <> 'tercero' OR
        (nombre_receptor IS NOT NULL AND length(trim(nombre_receptor)) >= 2))
);
COMMIT;

-- Verificación opcional de estructura, sin modificar datos.
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN (
    'solicitud_etapa', 'solicitud_historial', 'solicitud_observacion',
    'solicitud_resultado', 'solicitud_entrega') ORDER BY table_name;
