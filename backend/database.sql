-- ESQUEMA MAESTRO DE REFERENCIA: acceso/cuenta y M03 Fases 1–6.
-- Creación desde cero. NO ejecutar sobre una base existente.
-- Para actualizar Fases 1–3 usar exclusivamente el SQL manual de Fases 4–6.
-- No contiene personas ni flujos institucionales de ejemplo.
-- Conserva el alcance previo de este archivo; el esquema RAG/chat se gestiona aparte.
BEGIN;


CREATE EXTENSION IF NOT EXISTS citext;

CREATE OR REPLACE FUNCTION actualizar_fecha_actualizacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- USUARIO
CREATE TABLE usuario (
    id_usuario BIGSERIAL PRIMARY KEY,

    nombres VARCHAR(100) NOT NULL,

    apellidos VARCHAR(100) NOT NULL,

    contrasena_hash TEXT,

    estado VARCHAR(30) NOT NULL
        DEFAULT 'pendiente_verificacion',

    fecha_ultimo_acceso TIMESTAMPTZ,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_usuario_nombres_no_vacios
        CHECK (LENGTH(TRIM(nombres)) >= 2),

    CONSTRAINT ck_usuario_apellidos_no_vacios
        CHECK (LENGTH(TRIM(apellidos)) >= 2),

    CONSTRAINT ck_usuario_estado
        CHECK (
            estado IN (
                'pendiente_verificacion',
                'activo',
                'bloqueado',
                'inactivo'
            )
        )
);

-- USUARIO_CORREO
CREATE TABLE usuario_correo (
    id_usuario_correo BIGSERIAL PRIMARY KEY,

    id_usuario BIGINT NOT NULL,

    correo CITEXT NOT NULL,

    tipo VARCHAR(20) NOT NULL,

    es_principal BOOLEAN NOT NULL DEFAULT FALSE,

    verificado BOOLEAN NOT NULL DEFAULT FALSE,

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    fecha_verificacion TIMESTAMPTZ,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_usuario_correo_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT uq_usuario_correo
        UNIQUE (correo),

    CONSTRAINT ck_usuario_correo_tipo
        CHECK (
            tipo IN (
                'institucional',
                'personal'
            )
        ),

    CONSTRAINT ck_usuario_correo_verificacion
        CHECK (
            (
                verificado = FALSE
                AND fecha_verificacion IS NULL
            )
            OR
            (
                verificado = TRUE
                AND fecha_verificacion IS NOT NULL
            )
        )
);

-- ROL
CREATE TABLE rol (
    id_rol BIGSERIAL PRIMARY KEY,

    nombre VARCHAR(50) NOT NULL,

    descripcion TEXT,

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_rol_nombre
        UNIQUE (nombre),

    CONSTRAINT ck_rol_nombre_no_vacio
        CHECK (LENGTH(TRIM(nombre)) >= 3)
);

-- USUARIO_ROL
CREATE TABLE usuario_rol (
    id_usuario_rol BIGSERIAL PRIMARY KEY,

    id_usuario BIGINT NOT NULL,

    id_rol BIGINT NOT NULL,

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    asignado_por BIGINT,

    fecha_asignacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_revocacion TIMESTAMPTZ,

    CONSTRAINT fk_usuario_rol_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT fk_usuario_rol_rol
        FOREIGN KEY (id_rol)
        REFERENCES rol(id_rol),

    CONSTRAINT fk_usuario_rol_asignado_por
        FOREIGN KEY (asignado_por)
        REFERENCES usuario(id_usuario)
        ON DELETE SET NULL,

    CONSTRAINT uq_usuario_rol
        UNIQUE (id_usuario, id_rol),

    CONSTRAINT ck_usuario_rol_revocacion
        CHECK (
            (
                activo = TRUE
                AND fecha_revocacion IS NULL
            )
            OR
            (
                activo = FALSE
            )
        )
);

-- SESION_USUARIO
CREATE TABLE sesion_usuario (
    id_sesion BIGSERIAL PRIMARY KEY,

    id_usuario BIGINT NOT NULL,

    identificador_sesion UUID NOT NULL
        DEFAULT gen_random_uuid(),

    refresh_token_hash VARCHAR(64) NOT NULL,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_ultima_actividad TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_expiracion TIMESTAMPTZ NOT NULL,

    fecha_revocacion TIMESTAMPTZ,

    motivo_revocacion VARCHAR(100),

    direccion_ip INET,

    user_agent TEXT,

    CONSTRAINT fk_sesion_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT uq_sesion_identificador
        UNIQUE (identificador_sesion),

    CONSTRAINT uq_sesion_refresh_token_hash
        UNIQUE (refresh_token_hash),

    CONSTRAINT ck_sesion_expiracion
        CHECK (fecha_expiracion > fecha_creacion),

    CONSTRAINT ck_sesion_revocacion
        CHECK (
            fecha_revocacion IS NULL
            OR fecha_revocacion >= fecha_creacion
        )
);

-- TOKEN_VERIFICACION_CORREO
CREATE TABLE token_verificacion_correo (
    id_token_verificacion BIGSERIAL PRIMARY KEY,

    id_usuario_correo BIGINT NOT NULL,

    token_hash VARCHAR(64) NOT NULL,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_expiracion TIMESTAMPTZ NOT NULL,

    fecha_utilizacion TIMESTAMPTZ,

    fecha_revocacion TIMESTAMPTZ,

    direccion_ip_solicitud INET,

    CONSTRAINT fk_token_verificacion_correo
        FOREIGN KEY (id_usuario_correo)
        REFERENCES usuario_correo(id_usuario_correo)
        ON DELETE CASCADE,

    CONSTRAINT uq_token_verificacion_hash
        UNIQUE (token_hash),

    CONSTRAINT ck_token_verificacion_expiracion
        CHECK (fecha_expiracion > fecha_creacion),

    CONSTRAINT ck_token_verificacion_utilizacion
        CHECK (
            fecha_utilizacion IS NULL
            OR fecha_utilizacion >= fecha_creacion
        ),

    CONSTRAINT ck_token_verificacion_revocacion
        CHECK (
            fecha_revocacion IS NULL
            OR fecha_revocacion >= fecha_creacion
        )
);

-- TOKEN_RECUPERACION_CONTRASENA
CREATE TABLE token_recuperacion_contrasena (
    id_token_recuperacion BIGSERIAL PRIMARY KEY,

    id_usuario BIGINT NOT NULL,

    token_hash VARCHAR(64) NOT NULL,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_expiracion TIMESTAMPTZ NOT NULL,

    fecha_utilizacion TIMESTAMPTZ,

    fecha_revocacion TIMESTAMPTZ,

    direccion_ip_solicitud INET,

    CONSTRAINT fk_token_recuperacion_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT uq_token_recuperacion_hash
        UNIQUE (token_hash),

    CONSTRAINT ck_token_recuperacion_expiracion
        CHECK (fecha_expiracion > fecha_creacion),

    CONSTRAINT ck_token_recuperacion_utilizacion
        CHECK (
            fecha_utilizacion IS NULL
            OR fecha_utilizacion >= fecha_creacion
        ),

    CONSTRAINT ck_token_recuperacion_revocacion
        CHECK (
            fecha_revocacion IS NULL
            OR fecha_revocacion >= fecha_creacion
        )
);

-- EVENTO_AUTENTICACION
CREATE TABLE evento_autenticacion (
    id_evento_autenticacion BIGSERIAL PRIMARY KEY,

    id_usuario BIGINT,

    correo_intentado CITEXT,

    tipo_evento VARCHAR(40) NOT NULL,

    exitoso BOOLEAN NOT NULL,

    motivo_fallo VARCHAR(100),

    direccion_ip INET,

    user_agent TEXT,

    fecha_evento TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_evento_autenticacion_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE SET NULL,

    CONSTRAINT ck_evento_autenticacion_tipo
        CHECK (
            tipo_evento IN (
                'registro',
                'verificacion_correo',
                'inicio_sesion',
                'renovacion_sesion',
                'cierre_sesion',
                'solicitud_recuperacion',
                'cambio_contrasena',
                'cambio_correo',
                'bloqueo_cuenta',
                'desbloqueo_cuenta'
            )
        )
);

-- AUDITORIA
CREATE TABLE auditoria (
    id_auditoria BIGSERIAL PRIMARY KEY,

    id_usuario_actor BIGINT,

    accion VARCHAR(100) NOT NULL,

    modulo VARCHAR(50) NOT NULL,

    entidad VARCHAR(100),

    id_entidad VARCHAR(100),

    exitoso BOOLEAN NOT NULL DEFAULT TRUE,

    detalle JSONB,

    direccion_ip INET,

    user_agent TEXT,

    fecha_evento TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_auditoria_usuario_actor
        FOREIGN KEY (id_usuario_actor)
        REFERENCES usuario(id_usuario)
        ON DELETE SET NULL,

    CONSTRAINT ck_auditoria_accion_no_vacia
        CHECK (LENGTH(TRIM(accion)) >= 3),

    CONSTRAINT ck_auditoria_modulo_no_vacio
        CHECK (LENGTH(TRIM(modulo)) >= 3)
);

-- UNIDAD_ADMINISTRATIVA
CREATE TABLE unidad_administrativa (
    id_unidad BIGSERIAL PRIMARY KEY,

    nombre VARCHAR(120) NOT NULL,

    descripcion TEXT,

    activo BOOLEAN NOT NULL
        DEFAULT TRUE,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_unidad_administrativa_nombre
        UNIQUE (nombre),

    CONSTRAINT ck_unidad_administrativa_nombre_no_vacio
        CHECK (LENGTH(TRIM(nombre)) >= 3)
);

-- USUARIO_UNIDAD
CREATE TABLE usuario_unidad (
    id_usuario_unidad BIGSERIAL PRIMARY KEY,

    id_usuario BIGINT NOT NULL,

    id_unidad BIGINT NOT NULL,

    activo BOOLEAN NOT NULL
        DEFAULT TRUE,

    asignado_por BIGINT,

    fecha_asignacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_revocacion TIMESTAMPTZ,

    CONSTRAINT fk_usuario_unidad_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT fk_usuario_unidad_unidad
        FOREIGN KEY (id_unidad)
        REFERENCES unidad_administrativa(id_unidad)
        ON DELETE RESTRICT,

    CONSTRAINT fk_usuario_unidad_asignado_por
        FOREIGN KEY (asignado_por)
        REFERENCES usuario(id_usuario)
        ON DELETE SET NULL,

    CONSTRAINT uq_usuario_unidad
        UNIQUE (id_usuario, id_unidad),

    CONSTRAINT ck_usuario_unidad_revocacion
        CHECK (
            (
                activo = TRUE
                AND fecha_revocacion IS NULL
            )
            OR
            (
                activo = FALSE
            )
        )
);

-- TRAMITE
CREATE TABLE tramite (
    id_tramite BIGSERIAL PRIMARY KEY,

    nombre VARCHAR(200) NOT NULL,

    descripcion TEXT,

    activo BOOLEAN NOT NULL
        DEFAULT TRUE,

    publicado BOOLEAN NOT NULL
        DEFAULT FALSE,

    permite_solicitudes BOOLEAN NOT NULL
        DEFAULT FALSE,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_tramite_nombre
        UNIQUE (nombre),

    CONSTRAINT ck_tramite_nombre_no_vacio
        CHECK (LENGTH(TRIM(nombre)) >= 3),

    CONSTRAINT ck_tramite_publicacion
        CHECK (
            publicado = FALSE
            OR activo = TRUE
        ),

    CONSTRAINT ck_tramite_permite_solicitudes
        CHECK (
            permite_solicitudes = FALSE
            OR
            (
                activo = TRUE
                AND publicado = TRUE
            )
        ),

    tiempo_estimado TEXT,

    canales_atencion TEXT,

    instrucciones TEXT,

    condiciones TEXT,

    tipo_finalizacion VARCHAR(30),

    CONSTRAINT ck_tramite_tipo_finalizacion CHECK
        (tipo_finalizacion IN ('entrega', 'resultado_registrado', 'externo'))
);

-- TRAMITE_CAMPO
CREATE TABLE tramite_campo (
    id_campo BIGSERIAL PRIMARY KEY,

    id_tramite BIGINT NOT NULL,

    clave VARCHAR(80) NOT NULL,

    etiqueta VARCHAR(150) NOT NULL,

    descripcion TEXT,

    tipo_dato VARCHAR(30) NOT NULL,

    obligatorio BOOLEAN NOT NULL
        DEFAULT FALSE,

    orden INTEGER NOT NULL
        DEFAULT 1,

    configuracion JSONB,

    activo BOOLEAN NOT NULL
        DEFAULT TRUE,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_tramite_campo_tramite
        FOREIGN KEY (id_tramite)
        REFERENCES tramite(id_tramite)
        ON DELETE CASCADE,

    CONSTRAINT uq_tramite_campo_clave
        UNIQUE (
            id_tramite,
            clave
        ),

    CONSTRAINT ck_tramite_campo_clave_no_vacia
        CHECK (LENGTH(TRIM(clave)) >= 2),

    CONSTRAINT ck_tramite_campo_etiqueta_no_vacia
        CHECK (LENGTH(TRIM(etiqueta)) >= 2),

    CONSTRAINT ck_tramite_campo_tipo_dato
        CHECK (
            tipo_dato IN (
                'texto',
                'texto_largo',
                'entero',
                'decimal',
                'fecha',
                'booleano',
                'seleccion'
            )
        ),

    CONSTRAINT ck_tramite_campo_orden
        CHECK (orden > 0)
);

-- TRAMITE_ETAPA
CREATE TABLE tramite_etapa (
    id_etapa BIGSERIAL PRIMARY KEY,

    id_tramite BIGINT NOT NULL,

    id_unidad BIGINT,

    nombre VARCHAR(150) NOT NULL,

    descripcion TEXT,

    orden INTEGER NOT NULL,

    es_inicial BOOLEAN NOT NULL
        DEFAULT FALSE,

    es_final BOOLEAN NOT NULL
        DEFAULT FALSE,

    activo BOOLEAN NOT NULL
        DEFAULT TRUE,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_tramite_etapa_tramite
        FOREIGN KEY (id_tramite)
        REFERENCES tramite(id_tramite)
        ON DELETE CASCADE,

    CONSTRAINT fk_tramite_etapa_unidad
        FOREIGN KEY (id_unidad)
        REFERENCES unidad_administrativa(id_unidad)
        ON DELETE RESTRICT,

    CONSTRAINT uq_tramite_etapa_pertenencia UNIQUE (id_tramite, id_etapa),

    CONSTRAINT uq_tramite_etapa_orden
        UNIQUE (
            id_tramite,
            orden
        ),

    CONSTRAINT ck_tramite_etapa_nombre_no_vacio
        CHECK (LENGTH(TRIM(nombre)) >= 2),

    CONSTRAINT ck_tramite_etapa_orden
        CHECK (orden > 0),

    visible_solicitante BOOLEAN NOT NULL DEFAULT FALSE
);

-- TRAMITE_REQUISITO
CREATE TABLE tramite_requisito (
    id_requisito BIGSERIAL PRIMARY KEY,

    id_tramite BIGINT NOT NULL,

    nombre VARCHAR(200) NOT NULL,

    descripcion TEXT,

    obligatorio BOOLEAN NOT NULL
        DEFAULT TRUE,

    orden INTEGER NOT NULL
        DEFAULT 1,

    activo BOOLEAN NOT NULL
        DEFAULT TRUE,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_tramite_requisito_tramite
        FOREIGN KEY (id_tramite)
        REFERENCES tramite(id_tramite)
        ON DELETE CASCADE,

    CONSTRAINT uq_tramite_requisito_nombre
        UNIQUE (id_tramite, nombre),

    CONSTRAINT ck_tramite_requisito_nombre_no_vacio
        CHECK (LENGTH(TRIM(nombre)) >= 2),

    CONSTRAINT ck_tramite_requisito_orden
        CHECK (orden > 0),

    id_etapa BIGINT,

    CONSTRAINT fk_tramite_requisito_etapa FOREIGN KEY (id_tramite, id_etapa) REFERENCES tramite_etapa(id_tramite, id_etapa) ON DELETE RESTRICT,

    requiere_presentacion_fisica BOOLEAN NOT NULL DEFAULT FALSE,

    condicion JSONB,

    CONSTRAINT ck_tramite_requisito_condicion CHECK
        (condicion IS NULL OR (jsonb_typeof(condicion) = 'object'
            AND condicion->>'operador' = 'igual'
            AND condicion->>'origen' IN ('solicitud_dato', 'perfil_academico')))
);

-- TRAMITE_REQUISITO_ECONOMICO
CREATE TABLE tramite_requisito_economico (
    id_requisito_economico BIGSERIAL PRIMARY KEY,

    id_requisito BIGINT NOT NULL,

    concepto VARCHAR(200) NOT NULL,

    monto NUMERIC(12, 2) NOT NULL,

    moneda VARCHAR(3) NOT NULL
        DEFAULT 'BOB',

    gestion SMALLINT NOT NULL,

    codigo_concepto_externo VARCHAR(100),

    activo BOOLEAN NOT NULL
        DEFAULT TRUE,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_tramite_requisito_economico_requisito
        FOREIGN KEY (id_requisito)
        REFERENCES tramite_requisito(id_requisito)
        ON DELETE CASCADE,

    CONSTRAINT uq_tramite_requisito_economico_gestion
        UNIQUE (
            id_requisito,
            gestion
        ),

    CONSTRAINT ck_tramite_requisito_economico_concepto
        CHECK (LENGTH(TRIM(concepto)) >= 2),

    CONSTRAINT ck_tramite_requisito_economico_monto
        CHECK (monto > 0),

    CONSTRAINT ck_tramite_requisito_economico_moneda
        CHECK (LENGTH(TRIM(moneda)) = 3),

    CONSTRAINT ck_tramite_requisito_economico_gestion
        CHECK (
            gestion >= 2000
            AND gestion <= 2100
        )
);

-- PERFIL_ACADEMICO
CREATE TABLE perfil_academico (
    id_perfil BIGSERIAL PRIMARY KEY,

    id_usuario BIGINT NOT NULL,

    codigo_estudiante VARCHAR(50),

    sede VARCHAR(100),

    carrera_programa VARCHAR(200),

    nivel_academico VARCHAR(100),

    documento_identidad VARCHAR(50),

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_perfil_academico_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT uq_perfil_academico_usuario
        UNIQUE (id_usuario),

    CONSTRAINT ck_perfil_academico_codigo_estudiante
        CHECK (
            codigo_estudiante IS NULL
            OR LENGTH(TRIM(codigo_estudiante)) >= 1
        ),

    CONSTRAINT ck_perfil_academico_sede
        CHECK (
            sede IS NULL
            OR LENGTH(TRIM(sede)) >= 2
        ),

    CONSTRAINT ck_perfil_academico_carrera_programa
        CHECK (
            carrera_programa IS NULL
            OR LENGTH(TRIM(carrera_programa)) >= 2
        ),

    CONSTRAINT ck_perfil_academico_nivel_academico
        CHECK (
            nivel_academico IS NULL
            OR LENGTH(TRIM(nivel_academico)) >= 2
        ),

    CONSTRAINT ck_perfil_academico_documento_identidad
        CHECK (
            documento_identidad IS NULL
            OR LENGTH(TRIM(documento_identidad)) >= 3
        )
);

-- SOLICITUD
CREATE TABLE solicitud (
    id_solicitud BIGSERIAL PRIMARY KEY,

    id_solicitante BIGINT NOT NULL,

    id_tramite BIGINT NOT NULL,

    estado VARCHAR(30) NOT NULL
        DEFAULT 'borrador',

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_envio TIMESTAMPTZ,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_solicitud_solicitante
        FOREIGN KEY (id_solicitante)
        REFERENCES usuario(id_usuario)
        ON DELETE RESTRICT,

    CONSTRAINT fk_solicitud_tramite
        FOREIGN KEY (id_tramite)
        REFERENCES tramite(id_tramite)
        ON DELETE RESTRICT,

    CONSTRAINT ck_solicitud_fecha_envio_cronologia
        CHECK (
            fecha_envio IS NULL
            OR fecha_envio >= fecha_creacion
        ),

    id_etapa_actual BIGINT,

    CONSTRAINT ck_solicitud_proceso_etapa CHECK (estado <> 'en_proceso' OR id_etapa_actual IS NOT NULL),

    nombre_tramite_snapshot VARCHAR(200),

    tipo_finalizacion VARCHAR(30),

    CONSTRAINT ck_solicitud_tipo_finalizacion CHECK
        (tipo_finalizacion IN ('entrega', 'resultado_registrado', 'externo')),

    CONSTRAINT ck_solicitud_estado CHECK (estado IN (
        'borrador', 'pendiente_recepcion', 'en_revision', 'en_proceso',
        'lista_para_entrega', 'finalizada', 'cancelada', 'rechazada')),

    CONSTRAINT ck_solicitud_fecha_envio CHECK (
        (estado = 'borrador' AND fecha_envio IS NULL)
        OR estado = 'cancelada'
        OR (estado NOT IN ('borrador', 'cancelada') AND fecha_envio IS NOT NULL))
);

-- SOLICITUD_DATO
CREATE TABLE solicitud_dato (
    id_solicitud_dato BIGSERIAL PRIMARY KEY,

    id_solicitud BIGINT NOT NULL,

    id_campo BIGINT NOT NULL,

    valor JSONB NOT NULL,

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_solicitud_dato_solicitud
        FOREIGN KEY (id_solicitud)
        REFERENCES solicitud(id_solicitud)
        ON DELETE CASCADE,

    CONSTRAINT fk_solicitud_dato_campo
        FOREIGN KEY (id_campo)
        REFERENCES tramite_campo(id_campo)
        ON DELETE RESTRICT,

    CONSTRAINT uq_solicitud_dato_campo
        UNIQUE (
            id_solicitud,
            id_campo
        ),

    CONSTRAINT ck_solicitud_dato_valor
        CHECK (
            valor <> 'null'::jsonb
        ),

    clave_snapshot VARCHAR(100),

    etiqueta_snapshot VARCHAR(200)
);

-- SOLICITUD_RECEPCION
CREATE TABLE solicitud_recepcion (
    id_recepcion BIGSERIAL PRIMARY KEY,

    id_solicitud BIGINT NOT NULL,

    id_usuario_receptor BIGINT NOT NULL,

    fecha_recepcion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_solicitud_recepcion_solicitud
        FOREIGN KEY (id_solicitud)
        REFERENCES solicitud(id_solicitud)
        ON DELETE RESTRICT,

    CONSTRAINT fk_solicitud_recepcion_usuario
        FOREIGN KEY (id_usuario_receptor)
        REFERENCES usuario(id_usuario)
        ON DELETE RESTRICT,

    CONSTRAINT uq_solicitud_recepcion_solicitud
        UNIQUE (
            id_solicitud
        )
);

-- SOLICITUD_ETAPA
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

-- SOLICITUD_REQUISITO
CREATE TABLE solicitud_requisito (
    id_solicitud_requisito BIGSERIAL PRIMARY KEY,

    id_solicitud BIGINT NOT NULL,

    id_requisito_origen BIGINT,

    nombre VARCHAR(200) NOT NULL,

    descripcion TEXT,

    obligatorio BOOLEAN NOT NULL,

    orden INTEGER NOT NULL,

    id_requisito_economico_origen BIGINT,

    concepto_economico VARCHAR(200),

    monto_economico NUMERIC(12, 2),

    moneda VARCHAR(3),

    gestion SMALLINT,

    codigo_concepto_externo VARCHAR(100),

    numero_factura VARCHAR(150),

    fecha_creacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_solicitud_requisito_solicitud
        FOREIGN KEY (id_solicitud)
        REFERENCES solicitud(id_solicitud)
        ON DELETE CASCADE,

    CONSTRAINT fk_solicitud_requisito_origen
        FOREIGN KEY (id_requisito_origen)
        REFERENCES tramite_requisito(id_requisito)
        ON DELETE SET NULL,

    CONSTRAINT fk_solicitud_requisito_economico_origen
        FOREIGN KEY (id_requisito_economico_origen)
        REFERENCES tramite_requisito_economico(
            id_requisito_economico
        )
        ON DELETE SET NULL,

    CONSTRAINT uq_solicitud_requisito_origen
        UNIQUE (
            id_solicitud,
            id_requisito_origen
        ),

    CONSTRAINT ck_solicitud_requisito_nombre
        CHECK (
            LENGTH(TRIM(nombre)) >= 2
        ),

    CONSTRAINT ck_solicitud_requisito_orden
        CHECK (
            orden > 0
        ),

    CONSTRAINT ck_solicitud_requisito_economico
        CHECK (
            (
                concepto_economico IS NULL
                AND monto_economico IS NULL
                AND moneda IS NULL
                AND gestion IS NULL
                AND codigo_concepto_externo IS NULL
            )
            OR
            (
                concepto_economico IS NOT NULL
                AND monto_economico IS NOT NULL
                AND moneda IS NOT NULL
                AND gestion IS NOT NULL
            )
        ),

    CONSTRAINT ck_solicitud_requisito_concepto_economico
        CHECK (
            concepto_economico IS NULL
            OR LENGTH(TRIM(concepto_economico)) >= 2
        ),

    CONSTRAINT ck_solicitud_requisito_monto_economico
        CHECK (
            monto_economico IS NULL
            OR monto_economico > 0
        ),

    CONSTRAINT ck_solicitud_requisito_moneda
        CHECK (
            moneda IS NULL
            OR LENGTH(TRIM(moneda)) = 3
        ),

    CONSTRAINT ck_solicitud_requisito_gestion
        CHECK (
            gestion IS NULL
            OR (
                gestion >= 2000
                AND gestion <= 2100
            )
        ),

    CONSTRAINT ck_solicitud_requisito_numero_factura
        CHECK (
            numero_factura IS NULL
            OR LENGTH(TRIM(numero_factura)) >= 1
        ),

    estado_verificacion VARCHAR(20)
NOT NULL
DEFAULT 'pendiente',

    id_usuario_verificador BIGINT,

    fecha_verificacion TIMESTAMPTZ,

    detalle_verificacion TEXT,

    CONSTRAINT fk_solicitud_requisito_usuario_verificador
FOREIGN KEY (id_usuario_verificador)
REFERENCES usuario(id_usuario)
ON DELETE RESTRICT,

    CONSTRAINT ck_solicitud_requisito_estado_verificacion
CHECK (
    estado_verificacion IN (
        'pendiente',
        'cumple',
        'no_cumple'
    )
),

    CONSTRAINT ck_solicitud_requisito_verificacion_consistente
CHECK (
    (
        estado_verificacion = 'pendiente'
        AND id_usuario_verificador IS NULL
        AND fecha_verificacion IS NULL
    )
    OR
    (
        estado_verificacion IN (
            'cumple',
            'no_cumple'
        )
        AND id_usuario_verificador IS NOT NULL
        AND fecha_verificacion IS NOT NULL
    )
),

    CONSTRAINT ck_solicitud_requisito_detalle_verificacion
CHECK (
    detalle_verificacion IS NULL
    OR LENGTH(TRIM(detalle_verificacion)) >= 1
),

    id_solicitud_etapa BIGINT,

    requiere_presentacion_fisica BOOLEAN NOT NULL DEFAULT FALSE,

    presentado BOOLEAN NOT NULL DEFAULT FALSE,

    fecha_presentacion TIMESTAMPTZ,

    id_usuario_presentacion BIGINT REFERENCES usuario(id_usuario) ON DELETE RESTRICT,

    condicion_snapshot JSONB,

    CONSTRAINT fk_solicitud_requisito_etapa FOREIGN KEY (id_solicitud, id_solicitud_etapa)
        REFERENCES solicitud_etapa(id_solicitud, id_solicitud_etapa),

    CONSTRAINT uq_solicitud_requisito_pertenencia UNIQUE (id_solicitud, id_solicitud_requisito),

    CONSTRAINT ck_solicitud_requisito_presentacion CHECK (
        (NOT presentado AND fecha_presentacion IS NULL AND id_usuario_presentacion IS NULL)
        OR (presentado AND requiere_presentacion_fisica AND fecha_presentacion IS NOT NULL
            AND id_usuario_presentacion IS NOT NULL AND fecha_presentacion >= fecha_creacion))
);

-- SOLICITUD_PAGO_VERIFICACION
CREATE TABLE solicitud_pago_verificacion (
    id_verificacion_pago BIGSERIAL PRIMARY KEY,

    id_solicitud_requisito BIGINT NOT NULL,

    id_usuario_verificador BIGINT NOT NULL,

    numero_factura_consultado VARCHAR(150) NOT NULL,

    codigo_concepto_consultado VARCHAR(100) NOT NULL,

    codigo_concepto_reportado VARCHAR(100),

    estado_factura_reportado VARCHAR(50),

    monto_reportado NUMERIC(12, 2),

    moneda_reportada VARCHAR(3),

    estado VARCHAR(30) NOT NULL,

    detalle_respuesta JSONB,

    fecha_verificacion TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_pago_verificacion_solicitud_requisito
        FOREIGN KEY (id_solicitud_requisito)
        REFERENCES solicitud_requisito(
            id_solicitud_requisito
        )
        ON DELETE RESTRICT,

    CONSTRAINT fk_pago_verificacion_usuario
        FOREIGN KEY (id_usuario_verificador)
        REFERENCES usuario(id_usuario)
        ON DELETE RESTRICT,

    CONSTRAINT ck_pago_verificacion_estado
        CHECK (
            estado IN (
                'verificado',
                'no_verificado',
                'error'
            )
        ),

    CONSTRAINT ck_pago_verificacion_numero_factura
        CHECK (
            LENGTH(TRIM(numero_factura_consultado)) >= 1
        ),

    CONSTRAINT ck_pago_verificacion_codigo_consultado
        CHECK (
            LENGTH(TRIM(codigo_concepto_consultado)) >= 1
        ),

    CONSTRAINT ck_pago_verificacion_codigo_reportado
        CHECK (
            codigo_concepto_reportado IS NULL
            OR LENGTH(TRIM(codigo_concepto_reportado)) >= 1
        ),

    CONSTRAINT ck_pago_verificacion_estado_factura_reportado
        CHECK (
            estado_factura_reportado IS NULL
            OR LENGTH(TRIM(estado_factura_reportado)) >= 1
        ),

    CONSTRAINT ck_pago_verificacion_monto
        CHECK (
            monto_reportado IS NULL
            OR monto_reportado > 0
        ),

    CONSTRAINT ck_pago_verificacion_moneda
        CHECK (
            moneda_reportada IS NULL
            OR LENGTH(TRIM(moneda_reportada)) = 3
        )
);



-- SOLICITUD_OBSERVACION
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

-- SOLICITUD_RESULTADO
CREATE TABLE solicitud_resultado (
    id_resultado BIGSERIAL PRIMARY KEY,

    id_solicitud BIGINT NOT NULL UNIQUE REFERENCES solicitud(id_solicitud) ON DELETE RESTRICT,

    tipo_finalizacion VARCHAR(30) NOT NULL CHECK (tipo_finalizacion IN ('entrega', 'resultado_registrado', 'externo')),

    detalle TEXT,

    id_usuario_registro BIGINT NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,

    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- SOLICITUD_ENTREGA
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

-- SOLICITUD_HISTORIAL
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

-- Referencia circular entre solicitud y su etapa actual.
ALTER TABLE solicitud ADD CONSTRAINT fk_solicitud_etapa_actual
    FOREIGN KEY (id_solicitud, id_etapa_actual)
    REFERENCES solicitud_etapa(id_solicitud, id_solicitud_etapa);

-- Índices y actualización automática de fechas.
CREATE TRIGGER trg_usuario_fecha_actualizacion
BEFORE UPDATE ON usuario
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_usuario_estado
    ON usuario (estado);

CREATE TRIGGER trg_usuario_correo_fecha_actualizacion
BEFORE UPDATE ON usuario_correo
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE UNIQUE INDEX uq_usuario_correo_principal_activo
    ON usuario_correo (id_usuario)
    WHERE es_principal = TRUE
      AND activo = TRUE;

CREATE INDEX idx_usuario_correo_usuario
    ON usuario_correo (id_usuario);

CREATE INDEX idx_usuario_correo_busqueda
    ON usuario_correo (correo);

CREATE TRIGGER trg_rol_fecha_actualizacion
BEFORE UPDATE ON rol
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_usuario_rol_usuario
    ON usuario_rol (id_usuario);

CREATE INDEX idx_usuario_rol_rol
    ON usuario_rol (id_rol);

CREATE INDEX idx_usuario_rol_activo
    ON usuario_rol (id_usuario, activo);

CREATE INDEX idx_sesion_usuario
    ON sesion_usuario (id_usuario);

CREATE INDEX idx_sesion_usuario_vigente
    ON sesion_usuario (
        id_usuario,
        fecha_expiracion
    )
    WHERE fecha_revocacion IS NULL;

CREATE INDEX idx_sesion_expiracion
    ON sesion_usuario (fecha_expiracion);

CREATE INDEX idx_token_verificacion_correo
    ON token_verificacion_correo (id_usuario_correo);

CREATE INDEX idx_token_verificacion_expiracion
    ON token_verificacion_correo (fecha_expiracion)
    WHERE fecha_utilizacion IS NULL
      AND fecha_revocacion IS NULL;

CREATE INDEX idx_token_recuperacion_usuario
    ON token_recuperacion_contrasena (id_usuario);

CREATE INDEX idx_token_recuperacion_expiracion
    ON token_recuperacion_contrasena (fecha_expiracion)
    WHERE fecha_utilizacion IS NULL
      AND fecha_revocacion IS NULL;

CREATE INDEX idx_evento_autenticacion_usuario
    ON evento_autenticacion (id_usuario);

CREATE INDEX idx_evento_autenticacion_correo_fecha
    ON evento_autenticacion (
        correo_intentado,
        fecha_evento DESC
    );

CREATE INDEX idx_evento_autenticacion_ip_fecha
    ON evento_autenticacion (
        direccion_ip,
        fecha_evento DESC
    );

CREATE INDEX idx_evento_autenticacion_fallido
    ON evento_autenticacion (fecha_evento DESC)
    WHERE exitoso = FALSE;

CREATE INDEX idx_auditoria_usuario
    ON auditoria (id_usuario_actor);

CREATE INDEX idx_auditoria_fecha
    ON auditoria (fecha_evento DESC);

CREATE INDEX idx_auditoria_modulo
    ON auditoria (
        modulo,
        fecha_evento DESC
    );

CREATE INDEX idx_auditoria_entidad
    ON auditoria (
        entidad,
        id_entidad
    );

CREATE TRIGGER trg_unidad_administrativa_fecha_actualizacion
BEFORE UPDATE ON unidad_administrativa
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_unidad_administrativa_activo
    ON unidad_administrativa (activo);

CREATE INDEX idx_usuario_unidad_usuario
    ON usuario_unidad (id_usuario);

CREATE INDEX idx_usuario_unidad_unidad
    ON usuario_unidad (id_unidad);

CREATE INDEX idx_usuario_unidad_activo
    ON usuario_unidad (
        id_unidad,
        activo
    );

CREATE TRIGGER trg_tramite_fecha_actualizacion
BEFORE UPDATE ON tramite
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_tramite_activo
    ON tramite (activo);

CREATE INDEX idx_tramite_publicado
    ON tramite (publicado);

CREATE INDEX idx_tramite_catalogo
    ON tramite (
        activo,
        publicado
    );

CREATE TRIGGER trg_tramite_requisito_fecha_actualizacion
BEFORE UPDATE ON tramite_requisito
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_tramite_requisito_tramite
    ON tramite_requisito (id_tramite);

CREATE INDEX idx_tramite_requisito_tramite_activo
    ON tramite_requisito (
        id_tramite,
        activo
    );

CREATE INDEX idx_tramite_requisito_orden
    ON tramite_requisito (
        id_tramite,
        orden
    );

CREATE TRIGGER trg_tramite_requisito_economico_fecha_actualizacion
BEFORE UPDATE ON tramite_requisito_economico
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_tramite_requisito_economico_requisito
    ON tramite_requisito_economico (id_requisito);

CREATE INDEX idx_tramite_requisito_economico_gestion
    ON tramite_requisito_economico (
        gestion,
        activo
    );

CREATE INDEX idx_tramite_requisito_economico_codigo_externo
    ON tramite_requisito_economico (
        codigo_concepto_externo
    )
    WHERE codigo_concepto_externo IS NOT NULL;

CREATE TRIGGER trg_tramite_campo_fecha_actualizacion
BEFORE UPDATE ON tramite_campo
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_tramite_campo_tramite
    ON tramite_campo (id_tramite);

CREATE INDEX idx_tramite_campo_tramite_activo
    ON tramite_campo (
        id_tramite,
        activo
    );

CREATE INDEX idx_tramite_campo_orden
    ON tramite_campo (
        id_tramite,
        orden
    );

CREATE TRIGGER trg_tramite_etapa_fecha_actualizacion
BEFORE UPDATE ON tramite_etapa
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_tramite_etapa_tramite
    ON tramite_etapa (id_tramite);

CREATE INDEX idx_tramite_etapa_unidad
    ON tramite_etapa (id_unidad);

CREATE INDEX idx_tramite_etapa_tramite_activo
    ON tramite_etapa (
        id_tramite,
        activo
    );

CREATE UNIQUE INDEX uq_tramite_etapa_inicial_activa
    ON tramite_etapa (id_tramite)
    WHERE es_inicial = TRUE
      AND activo = TRUE;

CREATE UNIQUE INDEX uq_tramite_etapa_final_activa
    ON tramite_etapa (id_tramite)
    WHERE es_final = TRUE
      AND activo = TRUE;

CREATE TRIGGER trg_perfil_academico_fecha_actualizacion
BEFORE UPDATE ON perfil_academico
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_perfil_academico_codigo_estudiante
    ON perfil_academico (
        codigo_estudiante
    )
    WHERE codigo_estudiante IS NOT NULL;

CREATE INDEX idx_perfil_academico_documento_identidad
    ON perfil_academico (
        documento_identidad
    )
    WHERE documento_identidad IS NOT NULL;

CREATE TRIGGER trg_solicitud_fecha_actualizacion
BEFORE UPDATE ON solicitud
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_solicitud_solicitante
    ON solicitud (
        id_solicitante
    );

CREATE INDEX idx_solicitud_tramite
    ON solicitud (
        id_tramite
    );

CREATE INDEX idx_solicitud_estado
    ON solicitud (
        estado
    );

CREATE INDEX idx_solicitud_solicitante_estado
    ON solicitud (
        id_solicitante,
        estado
    );

CREATE INDEX idx_solicitud_fecha_creacion
    ON solicitud (
        fecha_creacion DESC
    );

CREATE TRIGGER trg_solicitud_dato_fecha_actualizacion
BEFORE UPDATE ON solicitud_dato
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_solicitud_dato_solicitud
    ON solicitud_dato (
        id_solicitud
    );

CREATE INDEX idx_solicitud_dato_campo
    ON solicitud_dato (
        id_campo
    );

CREATE TRIGGER trg_solicitud_requisito_fecha_actualizacion
BEFORE UPDATE ON solicitud_requisito
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_solicitud_requisito_solicitud
    ON solicitud_requisito (
        id_solicitud
    );

CREATE INDEX idx_solicitud_requisito_origen
    ON solicitud_requisito (
        id_requisito_origen
    )
    WHERE id_requisito_origen IS NOT NULL;

CREATE INDEX idx_solicitud_requisito_economico_origen
    ON solicitud_requisito (
        id_requisito_economico_origen
    )
    WHERE id_requisito_economico_origen IS NOT NULL;

CREATE INDEX idx_solicitud_requisito_numero_factura
    ON solicitud_requisito (
        numero_factura
    )
    WHERE numero_factura IS NOT NULL;

CREATE INDEX idx_solicitud_requisito_estado_verificacion
    ON solicitud_requisito (
        id_solicitud,
        estado_verificacion
    );

CREATE INDEX idx_solicitud_requisito_usuario_verificador
    ON solicitud_requisito (
        id_usuario_verificador
    )
    WHERE id_usuario_verificador IS NOT NULL;

CREATE INDEX idx_solicitud_recepcion_usuario
    ON solicitud_recepcion (
        id_usuario_receptor
    );

CREATE INDEX idx_solicitud_recepcion_fecha
    ON solicitud_recepcion (
        fecha_recepcion DESC
    );

CREATE INDEX idx_pago_verificacion_requisito
    ON solicitud_pago_verificacion (
        id_solicitud_requisito
    );

CREATE INDEX idx_pago_verificacion_usuario
    ON solicitud_pago_verificacion (
        id_usuario_verificador
    );

CREATE INDEX idx_pago_verificacion_estado
    ON solicitud_pago_verificacion (
        estado
    );

CREATE INDEX idx_pago_verificacion_fecha
    ON solicitud_pago_verificacion (
        fecha_verificacion DESC
    );

CREATE INDEX idx_pago_verificacion_numero_factura
    ON solicitud_pago_verificacion (
        numero_factura_consultado
    );

CREATE INDEX idx_pago_verificacion_codigo_consultado
    ON solicitud_pago_verificacion (
        codigo_concepto_consultado
    );

CREATE UNIQUE INDEX uq_pago_verificacion_factura_verificada
    ON solicitud_pago_verificacion (
        numero_factura_consultado
    )
    WHERE estado = 'verificado';

CREATE INDEX idx_tramite_requisito_etapa ON tramite_requisito(id_etapa);

CREATE UNIQUE INDEX uq_solicitud_etapa_inicial ON solicitud_etapa(id_solicitud) WHERE es_inicial = TRUE;
CREATE UNIQUE INDEX uq_solicitud_etapa_final ON solicitud_etapa(id_solicitud) WHERE es_final = TRUE;
CREATE UNIQUE INDEX uq_solicitud_etapa_en_curso ON solicitud_etapa(id_solicitud) WHERE estado = 'en_curso';

CREATE TRIGGER trg_solicitud_etapa_fecha_actualizacion BEFORE UPDATE ON solicitud_etapa
    FOR EACH ROW EXECUTE FUNCTION actualizar_fecha_actualizacion();

CREATE INDEX idx_solicitud_etapa_actual ON solicitud(id_etapa_actual);
CREATE INDEX idx_solicitud_fecha_envio ON solicitud(fecha_envio, id_solicitud)
    WHERE fecha_envio IS NOT NULL;

CREATE INDEX idx_solicitud_requisito_etapa ON solicitud_requisito(id_solicitud_etapa);

CREATE INDEX idx_solicitud_historial_cronologia ON solicitud_historial(id_solicitud, fecha_evento, id_historial);

CREATE INDEX idx_solicitud_observacion_estado ON solicitud_observacion(id_solicitud, estado);

-- Roles existentes del sistema (sin usuarios).
INSERT INTO rol (
    id_rol,
    nombre,
    descripcion,
    activo
)
VALUES
    (
        1,
        'solicitante',
        'Usuario que consulta información y solicita o realiza seguimiento de trámites.',
        TRUE
    ),
    (
        2,
        'personal_administrativo',
        'Personal autorizado para revisar, gestionar y actualizar trámites.',
        TRUE
    ),
    (
        3,
        'administrador',
        'Usuario autorizado para administrar cuentas, roles y configuración del sistema.',
        TRUE
    );

COMMIT;


BEGIN;

-- =========================================================
-- M03 - DATOS DE CONTACTO PROPIOS DE CADA SOLICITUD
-- =========================================================
--
-- Estos datos no modifican la cuenta del usuario.
-- Representan únicamente la información de contacto elegida
-- para una solicitud concreta.
--
-- Se mantienen NULL para conservar compatibilidad con
-- solicitudes históricas ya existentes.
-- =========================================================


ALTER TABLE solicitud
    ADD COLUMN nombre_contacto VARCHAR(200),
    ADD COLUMN telefono_contacto VARCHAR(30),
    ADD COLUMN correo_contacto VARCHAR(254);


ALTER TABLE solicitud
    ADD CONSTRAINT ck_solicitud_nombre_contacto
        CHECK (
            nombre_contacto IS NULL
            OR LENGTH(TRIM(nombre_contacto)) >= 2
        ),

    ADD CONSTRAINT ck_solicitud_telefono_contacto
        CHECK (
            telefono_contacto IS NULL
            OR LENGTH(TRIM(telefono_contacto)) >= 7
        ),

    ADD CONSTRAINT ck_solicitud_correo_contacto
        CHECK (
            correo_contacto IS NULL
            OR LENGTH(TRIM(correo_contacto)) >= 5
        );


COMMIT;


— —————————————————————————————————————————————


CREATE UNIQUE INDEX uq_usuario_correo_unico_activo
ON usuario_correo (id_usuario)
WHERE activo = TRUE;   — —————————————————————————————————————————————
 ALTER TABLE usuario
ADD COLUMN telefono VARCHAR(30);

ALTER TABLE usuario
ADD CONSTRAINT ck_usuario_telefono
CHECK (
    telefono IS NULL
    OR LENGTH(TRIM(telefono)) >= 7
); 

— —————————————————————————————————————————————
BEGIN;

DO $usuario_prueba$
DECLARE
    v_usuario BIGINT;
    v_rol_solicitante BIGINT;
    v_rol_administrativo BIGINT;

    v_correo CITEXT := 'solicitante.personal@gmail.com';

    /*
     * Contraseña:
     * Solicitante123!
     *
     * Hash Argon2 compatible con el utilizado
     * en el script de prueba generado previamente.
     */
    v_contrasena_hash TEXT :=
        '$argon2id$v=19$m=65536,t=3,p=4$jdzPk+lMYqfrDrJIW3v9gA$3bE8+HtCCyU9fPRARp6GxlKIxHsFlaMNOD2sRa2nea8';

BEGIN

    ------------------------------------------------------------
    -- 1. COMPROBAR ROLES
    ------------------------------------------------------------

    SELECT id_rol
    INTO v_rol_solicitante
    FROM rol
    WHERE nombre = 'solicitante'
      AND activo = TRUE;

    IF v_rol_solicitante IS NULL THEN
        RAISE EXCEPTION
            'No existe el rol activo solicitante.';
    END IF;


    SELECT id_rol
    INTO v_rol_administrativo
    FROM rol
    WHERE nombre = 'personal_administrativo'
      AND activo = TRUE;

    IF v_rol_administrativo IS NULL THEN
        RAISE EXCEPTION
            'No existe el rol activo personal_administrativo.';
    END IF;


    ------------------------------------------------------------
    -- 2. BUSCAR USUARIO SI YA EXISTE
    ------------------------------------------------------------

    SELECT u.id_usuario
    INTO v_usuario
    FROM usuario u
    JOIN usuario_correo c
      ON c.id_usuario = u.id_usuario
    WHERE c.correo = v_correo
    LIMIT 1;


    ------------------------------------------------------------
    -- 3. CREAR O ACTUALIZAR USUARIO
    ------------------------------------------------------------

    IF v_usuario IS NULL THEN

        INSERT INTO usuario (
            nombres,
            apellidos,
            telefono,
            contrasena_hash,
            estado
        )
        VALUES (
            'Usuario',
            'Solicitante Administrativo',
            '71234567',
            v_contrasena_hash,
            'activo'
        )
        RETURNING id_usuario
        INTO v_usuario;


        INSERT INTO usuario_correo (
            id_usuario,
            correo,
            tipo,
            es_principal,
            verificado,
            activo,
            fecha_verificacion
        )
        VALUES (
            v_usuario,
            v_correo,
            'personal',
            TRUE,
            TRUE,
            TRUE,
            CURRENT_TIMESTAMP
        );

    ELSE

        UPDATE usuario
        SET
            nombres = 'Usuario',
            apellidos = 'Solicitante Administrativo',
            telefono = '71234567',
            contrasena_hash = v_contrasena_hash,
            estado = 'activo',
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_usuario = v_usuario;


        UPDATE usuario_correo
        SET
            tipo = 'personal',
            es_principal = TRUE,
            verificado = TRUE,
            activo = TRUE,
            fecha_verificacion = COALESCE(
                fecha_verificacion,
                CURRENT_TIMESTAMP
            ),
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_usuario = v_usuario
          AND correo = v_correo;

    END IF;


    ------------------------------------------------------------
    -- 4. PERFIL ACADÉMICO
    ------------------------------------------------------------

    INSERT INTO perfil_academico (
        id_usuario,
        codigo_estudiante,
        sede,
        carrera_programa,
        nivel_academico,
        documento_identidad
    )
    VALUES (
        v_usuario,
        'PRUEBA-001',
        'La Paz',
        'Ingeniería de Sistemas',
        'Licenciatura',
        '1234567'
    )
    ON CONFLICT (id_usuario)
    DO UPDATE SET
        codigo_estudiante = EXCLUDED.codigo_estudiante,
        sede = EXCLUDED.sede,
        carrera_programa = EXCLUDED.carrera_programa,
        nivel_academico = EXCLUDED.nivel_academico,
        documento_identidad = EXCLUDED.documento_identidad,
        fecha_actualizacion = CURRENT_TIMESTAMP;


    ------------------------------------------------------------
    -- 5. ROL SOLICITANTE
    ------------------------------------------------------------

    INSERT INTO usuario_rol (
        id_usuario,
        id_rol,
        activo,
        fecha_revocacion
    )
    VALUES (
        v_usuario,
        v_rol_solicitante,
        TRUE,
        NULL
    )
    ON CONFLICT (id_usuario, id_rol)
    DO UPDATE SET
        activo = TRUE,
        fecha_revocacion = NULL;


    ------------------------------------------------------------
    -- 6. ROL PERSONAL ADMINISTRATIVO
    ------------------------------------------------------------

    INSERT INTO usuario_rol (
        id_usuario,
        id_rol,
        activo,
        fecha_revocacion
    )
    VALUES (
        v_usuario,
        v_rol_administrativo,
        TRUE,
        NULL
    )
    ON CONFLICT (id_usuario, id_rol)
    DO UPDATE SET
        activo = TRUE,
        fecha_revocacion = NULL;

END;
$usuario_prueba$;

COMMIT;


------------------------------------------------------------
-- COMPROBACIÓN
------------------------------------------------------------

SELECT
    u.id_usuario,
    u.nombres,
    u.apellidos,
    u.telefono,
    u.estado,
    c.correo,
    c.es_principal,
    c.verificado,
    c.activo AS correo_activo,
    p.documento_identidad,
    p.codigo_estudiante,
    p.sede,
    p.carrera_programa,
    p.nivel_academico,
    ARRAY(
        SELECT r.nombre
        FROM usuario_rol ur
        JOIN rol r
          ON r.id_rol = ur.id_rol
        WHERE ur.id_usuario = u.id_usuario
          AND ur.activo = TRUE
          AND r.activo = TRUE
        ORDER BY r.nombre
    ) AS roles_activos
FROM usuario u
JOIN usuario_correo c
  ON c.id_usuario = u.id_usuario
LEFT JOIN perfil_academico p
  ON p.id_usuario = u.id_usuario
WHERE c.correo = 'solicitante.personal@gmail.com';









— ———————————————————————————————


BEGIN;

CREATE TABLE IF NOT EXISTS usuario_identidad_externa (
    id_usuario_identidad BIGSERIAL PRIMARY KEY,

    id_usuario BIGINT NOT NULL,

    proveedor VARCHAR(50) NOT NULL,

    identificador_proveedor VARCHAR(255) NOT NULL,

    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_usuario_identidad_externa_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT uq_identidad_externa_proveedor_identificador
        UNIQUE (
            proveedor,
            identificador_proveedor
        ),

    CONSTRAINT uq_identidad_externa_usuario_proveedor
        UNIQUE (
            id_usuario,
            proveedor
        )
);

CREATE INDEX IF NOT EXISTS idx_identidad_externa_usuario
    ON usuario_identidad_externa (
        id_usuario
    );

CREATE INDEX IF NOT EXISTS idx_identidad_externa_proveedor
    ON usuario_identidad_externa (
        proveedor
    );

COMMIT;



— ————————————————————————————————






-- ============================================================
-- UCB ACADEMIC PROCEDURES PLATFORM
--
-- Valoración de respuestas del módulo informativo RAG
--
-- Fecha: 2026-10-06
-- ============================================================


BEGIN;


-- ============================================================
-- TABLA: chat_message_feedback
-- ============================================================
--
-- Una respuesta del asistente puede tener como máximo
-- una valoración activa:
--
--   1  = respuesta útil / like
--  -1  = respuesta no útil / dislike
--
-- La valoración puede modificarse posteriormente.
-- ============================================================

CREATE TABLE IF NOT EXISTS chat_message_feedback (

    id_feedback UUID
        PRIMARY KEY
        DEFAULT gen_random_uuid(),

    message_id UUID
        NOT NULL,

    rating SMALLINT
        NOT NULL,

    created_at TIMESTAMPTZ
        NOT NULL
        DEFAULT NOW(),

    updated_at TIMESTAMPTZ
        NOT NULL
        DEFAULT NOW(),


    CONSTRAINT fk_chat_message_feedback_message
        FOREIGN KEY (message_id)
        REFERENCES chat_message(id_message)
        ON DELETE CASCADE,


    CONSTRAINT uq_chat_message_feedback_message
        UNIQUE (message_id),


    CONSTRAINT ck_chat_message_feedback_rating
        CHECK (
            rating IN (-1, 1)
        )
);


-- ============================================================
-- ÍNDICE PARA CONSULTAS ESTADÍSTICAS
-- ============================================================

CREATE INDEX IF NOT EXISTS
    idx_chat_message_feedback_rating
ON chat_message_feedback(rating);


COMMIT;
