BEGIN;

CREATE EXTENSION IF NOT EXISTS citext;


-- =========================================================
-- FUNCION: ACTUALIZAR FECHA DE MODIFICACION
-- =========================================================

CREATE OR REPLACE FUNCTION actualizar_fecha_actualizacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =========================================================
-- TABLA: USUARIO
-- =========================================================

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


CREATE TRIGGER trg_usuario_fecha_actualizacion
BEFORE UPDATE ON usuario
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();


CREATE INDEX idx_usuario_estado
    ON usuario (estado);



-- =========================================================
-- TABLA: USUARIO_CORREO
-- =========================================================

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



-- =========================================================
-- TABLA: ROL
-- =========================================================

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


CREATE TRIGGER trg_rol_fecha_actualizacion
BEFORE UPDATE ON rol
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();



-- =========================================================
-- TABLA: USUARIO_ROL
-- =========================================================

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


CREATE INDEX idx_usuario_rol_usuario
    ON usuario_rol (id_usuario);


CREATE INDEX idx_usuario_rol_rol
    ON usuario_rol (id_rol);


CREATE INDEX idx_usuario_rol_activo
    ON usuario_rol (id_usuario, activo);



-- =========================================================
-- TABLA: SESION_USUARIO
-- =========================================================

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



-- =========================================================
-- TABLA: TOKEN_VERIFICACION_CORREO
-- =========================================================

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


CREATE INDEX idx_token_verificacion_correo
    ON token_verificacion_correo (id_usuario_correo);


CREATE INDEX idx_token_verificacion_expiracion
    ON token_verificacion_correo (fecha_expiracion)
    WHERE fecha_utilizacion IS NULL
      AND fecha_revocacion IS NULL;



-- =========================================================
-- TABLA: TOKEN_RECUPERACION_CONTRASENA
-- =========================================================

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


CREATE INDEX idx_token_recuperacion_usuario
    ON token_recuperacion_contrasena (id_usuario);


CREATE INDEX idx_token_recuperacion_expiracion
    ON token_recuperacion_contrasena (fecha_expiracion)
    WHERE fecha_utilizacion IS NULL
      AND fecha_revocacion IS NULL;



-- =========================================================
-- TABLA: EVENTO_AUTENTICACION
-- =========================================================

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



-- =========================================================
-- TABLA: AUDITORIA
-- =========================================================

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



-- =========================================================
-- REGISTROS: ROL
-- =========================================================

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



-- =========================================================
-- REGISTROS: USUARIO
-- =========================================================

INSERT INTO usuario (
    id_usuario,
    nombres,
    apellidos,
    contrasena_hash,
    estado
)
VALUES
    (
        1,
        'Usuario',
        'Prueba',
        '<HASH_ARGON2_USUARIO_PRUEBA>',
        'activo'
    ),
    (
        2,
        'Usuario',
        'Secundario',
        '<HASH_ARGON2_USUARIO_SECUNDARIO>',
        'activo'
    );



-- =========================================================
-- REGISTROS: USUARIO_CORREO
-- =========================================================

INSERT INTO usuario_correo (
    id_usuario_correo,
    id_usuario,
    correo,
    tipo,
    es_principal,
    verificado,
    activo,
    fecha_verificacion
)
VALUES
    (
        1,
        1,
        'usuario.prueba@ucb.edu.bo',
        'institucional',
        TRUE,
        TRUE,
        TRUE,
        CURRENT_TIMESTAMP
    ),
    (
        2,
        2,
        'usuario.secundario@ucb.edu.bo',
        'institucional',
        TRUE,
        FALSE,
        TRUE,
        NULL
    );



-- =========================================================
-- REGISTROS: USUARIO_ROL
-- =========================================================

INSERT INTO usuario_rol (
    id_usuario_rol,
    id_usuario,
    id_rol,
    activo,
    asignado_por
)
VALUES
    (
        1,
        1,
        1,
        TRUE,
        NULL
    ),
    (
        2,
        1,
        3,
        TRUE,
        NULL
    ),
    (
        3,
        2,
        1,
        TRUE,
        NULL
    );



-- =========================================================
-- AJUSTE DE SECUENCIAS
-- =========================================================

SELECT setval(
    pg_get_serial_sequence('usuario', 'id_usuario'),
    (SELECT MAX(id_usuario) FROM usuario)
);

SELECT setval(
    pg_get_serial_sequence('usuario_correo', 'id_usuario_correo'),
    (SELECT MAX(id_usuario_correo) FROM usuario_correo)
);

SELECT setval(
    pg_get_serial_sequence('rol', 'id_rol'),
    (SELECT MAX(id_rol) FROM rol)
);

SELECT setval(
    pg_get_serial_sequence('usuario_rol', 'id_usuario_rol'),
    (SELECT MAX(id_usuario_rol) FROM usuario_rol)
);


COMMIT;





















-- =========================================================
-- MODULO: GESTION Y SEGUIMIENTO
-- FASE 1: CATALOGO Y CONFIGURACION
-- =========================================================
--
-- Este bloque agrega la estructura base del modulo de
-- gestion y seguimiento de tramites.
--
-- IMPORTANTE:
-- La tabla tramite_etapa se crea como estructura configurable.
-- No se cargan procesos internos de tramites mientras estos
-- no hayan sido confirmados institucionalmente.
-- =========================================================

BEGIN;
-- =========================================================
-- TABLA: UNIDAD_ADMINISTRATIVA
-- =========================================================

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


CREATE TRIGGER trg_unidad_administrativa_fecha_actualizacion
BEFORE UPDATE ON unidad_administrativa
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();


CREATE INDEX idx_unidad_administrativa_activo
    ON unidad_administrativa (activo);



-- =========================================================
-- TABLA: USUARIO_UNIDAD
-- =========================================================

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


CREATE INDEX idx_usuario_unidad_usuario
    ON usuario_unidad (id_usuario);


CREATE INDEX idx_usuario_unidad_unidad
    ON usuario_unidad (id_unidad);


CREATE INDEX idx_usuario_unidad_activo
    ON usuario_unidad (
        id_unidad,
        activo
    );



-- =========================================================
-- TABLA: TRAMITE
-- =========================================================

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
        )
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



-- =========================================================
-- TABLA: TRAMITE_REQUISITO
-- =========================================================

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
        CHECK (orden > 0)
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



-- =========================================================
-- TABLA: TRAMITE_REQUISITO_ECONOMICO
-- =========================================================

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



-- =========================================================
-- TABLA: TRAMITE_CAMPO
-- =========================================================

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



-- =========================================================
-- TABLA: TRAMITE_ETAPA
-- =========================================================
--
-- Estructura configurable.
-- No se deben insertar etapas ni flujos de procesos internos
-- hasta contar con informacion institucional confirmada.
-- =========================================================

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

    CONSTRAINT uq_tramite_etapa_orden
        UNIQUE (
            id_tramite,
            orden
        ),

    CONSTRAINT ck_tramite_etapa_nombre_no_vacio
        CHECK (LENGTH(TRIM(nombre)) >= 2),

    CONSTRAINT ck_tramite_etapa_orden
        CHECK (orden > 0)
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

COMMIT;
















-- =========================================================
-- MODULO: GESTION Y SEGUIMIENTO
-- FASE 2: SOLICITUD DE TRAMITE POR EL SOLICITANTE
-- =========================================================
--
-- Este bloque agrega la estructura necesaria para que un
-- solicitante pueda crear, guardar y enviar solicitudes.
--
-- IMPORTANTE:
--
-- - No se utiliza codigo de ticket.
-- - No se almacenan documentos adjuntos.
-- - No se implementa todavia recepcion administrativa.
-- - No se implementan etapas ni flujo interno.
-- - Los datos especificos de cada tramite se obtienen desde
--   tramite_campo y se almacenan en solicitud_dato.
-- - Para requisitos economicos el solicitante proporciona
--   el numero de factura recibido luego de realizar el pago.
-- - El sistema no procesa ni realiza el cobro.
-- =========================================================



-- =========================================================
-- TABLA: PERFIL_ACADEMICO
-- =========================================================

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



-- =========================================================
-- TABLA: SOLICITUD
-- =========================================================

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

    CONSTRAINT ck_solicitud_estado
        CHECK (
            estado IN (
                'borrador',
                'pendiente_recepcion'
            )
        ),

    CONSTRAINT ck_solicitud_fecha_envio
        CHECK (
            (
                estado = 'borrador'
                AND fecha_envio IS NULL
            )
            OR
            (
                estado <> 'borrador'
                AND fecha_envio IS NOT NULL
            )
        ),

    CONSTRAINT ck_solicitud_fecha_envio_cronologia
        CHECK (
            fecha_envio IS NULL
            OR fecha_envio >= fecha_creacion
        )
);


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



-- =========================================================
-- TABLA: SOLICITUD_DATO
-- =========================================================
--
-- Guarda los valores ingresados para los campos configurados
-- en tramite_campo.
--
-- No se crean columnas especificas como:
-- sede_destino, motivo, carrera_destino, etc.
-- =========================================================

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
        )
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



-- =========================================================
-- TABLA: SOLICITUD_REQUISITO
-- =========================================================
--
-- Representa una fotografia de los requisitos aplicables
-- al momento de enviar formalmente una solicitud.
--
-- Los cambios posteriores realizados en tramite_requisito
-- o tramite_requisito_economico no modifican la informacion
-- historica almacenada en una solicitud ya enviada.
--
-- Para los requisitos economicos se puede almacenar el
-- numero de factura proporcionado por el solicitante.
--
-- La validacion de la factura ocurre posteriormente mediante
-- la API externa en Fase 3.
-- =========================================================

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
        )
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



-- =========================================================
-- MODULO: GESTION Y SEGUIMIENTO
-- FASE 3: RECEPCION Y GESTION ADMINISTRATIVA
-- =========================================================
--
-- Esta fase incorpora:
--
-- - bandeja administrativa de solicitudes;
-- - recepcion administrativa;
-- - estado en_revision;
-- - verificacion de requisitos;
-- - verificacion de facturas mediante una API externa;
-- - registro historico de los intentos de verificacion.
--
-- IMPORTANTE:
--
-- - No se asigna todavia una unidad receptora.
-- - No se ejecutan etapas del tramite.
-- - No se realizan derivaciones.
-- - No se implementan observaciones ni subsanaciones.
-- - No se procesa ni cobra dinero dentro del sistema.
-- - El numero de factura lo proporciona el solicitante.
-- - El codigo enviado a la API proviene de la configuracion
--   economica del tramite.
-- - La URL y credenciales de la API se parametrizan fuera
--   de la base de datos de negocio.
-- - La API mock sera un servicio HTTP independiente.
-- =========================================================



-- =========================================================
-- AMPLIACION DE ESTADOS DE SOLICITUD
-- =========================================================

ALTER TABLE solicitud
DROP CONSTRAINT ck_solicitud_estado;


ALTER TABLE solicitud
ADD CONSTRAINT ck_solicitud_estado
CHECK (
    estado IN (
        'borrador',
        'pendiente_recepcion',
        'en_revision'
    )
);



-- =========================================================
-- AMPLIACION: SOLICITUD_REQUISITO
-- =========================================================
--
-- Registra el resultado de la revision administrativa
-- correspondiente al snapshot de cada requisito.
--
-- Para requisitos economicos la comprobacion de pago
-- se realiza mediante la API externa.
-- =========================================================

ALTER TABLE solicitud_requisito
ADD COLUMN estado_verificacion VARCHAR(20)
NOT NULL
DEFAULT 'pendiente';


ALTER TABLE solicitud_requisito
ADD COLUMN id_usuario_verificador BIGINT;


ALTER TABLE solicitud_requisito
ADD COLUMN fecha_verificacion TIMESTAMPTZ;


ALTER TABLE solicitud_requisito
ADD COLUMN detalle_verificacion TEXT;


ALTER TABLE solicitud_requisito
ADD CONSTRAINT fk_solicitud_requisito_usuario_verificador
FOREIGN KEY (id_usuario_verificador)
REFERENCES usuario(id_usuario)
ON DELETE RESTRICT;


ALTER TABLE solicitud_requisito
ADD CONSTRAINT ck_solicitud_requisito_estado_verificacion
CHECK (
    estado_verificacion IN (
        'pendiente',
        'cumple',
        'no_cumple'
    )
);


ALTER TABLE solicitud_requisito
ADD CONSTRAINT ck_solicitud_requisito_verificacion_consistente
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
);


ALTER TABLE solicitud_requisito
ADD CONSTRAINT ck_solicitud_requisito_detalle_verificacion
CHECK (
    detalle_verificacion IS NULL
    OR LENGTH(TRIM(detalle_verificacion)) >= 1
);


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



-- =========================================================
-- TABLA: SOLICITUD_RECEPCION
-- =========================================================
--
-- Registra quien recibio formalmente la solicitud y cuando.
--
-- Una solicitud solamente puede tener una recepcion inicial.
--
-- No se registra una unidad receptora porque todavia no
-- conocemos institucionalmente que unidad inicia cada
-- procedimiento.
-- =========================================================

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


CREATE INDEX idx_solicitud_recepcion_usuario
    ON solicitud_recepcion (
        id_usuario_receptor
    );


CREATE INDEX idx_solicitud_recepcion_fecha
    ON solicitud_recepcion (
        fecha_recepcion DESC
    );



-- =========================================================
-- TABLA: SOLICITUD_PAGO_VERIFICACION
-- =========================================================
--
-- Registra cada intento realizado contra la API externa
-- para validar la factura asociada a un requisito economico.
--
-- El backend envia principalmente:
--
--   numero_factura
--   codigo_concepto
--
-- La API externa informa los datos disponibles sobre esa
-- factura.
--
-- El sistema compara posteriormente:
--
--   codigo esperado vs codigo reportado
--   monto esperado  vs monto reportado
--   moneda esperada vs moneda reportada
--   estado de la factura
--
-- ESTADOS:
--
-- verificado:
--     La respuesta permite acreditar correctamente el pago.
--
-- no_verificado:
--     La factura existe o fue consultada, pero no permite
--     acreditar el requisito.
--
-- error:
--     No fue posible realizar correctamente la consulta
--     externa, por ejemplo timeout o error HTTP.
--
-- IMPORTANTE:
--
-- Una misma factura puede tener varios intentos fallidos,
-- pero solamente UNA verificacion exitosa dentro del
-- sistema.
-- =========================================================

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