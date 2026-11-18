--
-- PostgreSQL database dump
--

\restrict YJYAnUi3QNuUagj1hckIeCT74N5kMw7M6KWrw4LnzxJ8PhxXWNEkF8W1wiBSLNm

-- Dumped from database version 17.10 (Debian 17.10-1.pgdg12+1)
-- Dumped by pg_dump version 17.10 (Debian 17.10-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: actualizar_fecha_actualizacion(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.actualizar_fecha_actualizacion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.fecha_actualizacion = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: archivo_documento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.archivo_documento (
    id_version_documento integer NOT NULL,
    nombre_archivo_original character varying(255),
    contenido_pdf bytea NOT NULL,
    tamano_bytes integer GENERATED ALWAYS AS (octet_length(contenido_pdf)) STORED,
    fecha_almacenamiento timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_archivo_documento_nombre CHECK (((nombre_archivo_original IS NULL) OR (length(TRIM(BOTH FROM nombre_archivo_original)) > 0))),
    CONSTRAINT ck_archivo_documento_tamano CHECK ((octet_length(contenido_pdf) > 0))
);


--
-- Name: TABLE archivo_documento; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.archivo_documento IS 'Almacena los archivos PDF originales asociados a cada version documental del sistema.';


--
-- Name: COLUMN archivo_documento.id_version_documento; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.archivo_documento.id_version_documento IS 'Identificador de la version documental. Clave primaria y foranea.';


--
-- Name: COLUMN archivo_documento.nombre_archivo_original; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.archivo_documento.nombre_archivo_original IS 'Nombre original del archivo PDF incorporado al sistema.';


--
-- Name: COLUMN archivo_documento.contenido_pdf; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.archivo_documento.contenido_pdf IS 'Contenido binario completo del archivo PDF original.';


--
-- Name: COLUMN archivo_documento.tamano_bytes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.archivo_documento.tamano_bytes IS 'Tamano del PDF en bytes, calculado automaticamente.';


--
-- Name: COLUMN archivo_documento.fecha_almacenamiento; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.archivo_documento.fecha_almacenamiento IS 'Fecha y hora en que el PDF fue almacenado en PostgreSQL.';


--
-- Name: auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auditoria (
    id_auditoria bigint NOT NULL,
    id_usuario_actor bigint,
    accion character varying(100) NOT NULL,
    modulo character varying(50) NOT NULL,
    entidad character varying(100),
    id_entidad character varying(100),
    exitoso boolean DEFAULT true NOT NULL,
    detalle jsonb,
    direccion_ip inet,
    user_agent text,
    fecha_evento timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_auditoria_accion_no_vacia CHECK ((length(TRIM(BOTH FROM accion)) >= 3)),
    CONSTRAINT ck_auditoria_modulo_no_vacio CHECK ((length(TRIM(BOTH FROM modulo)) >= 3))
);


--
-- Name: auditoria_id_auditoria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auditoria_id_auditoria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auditoria_id_auditoria_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auditoria_id_auditoria_seq OWNED BY public.auditoria.id_auditoria;


--
-- Name: chat_message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_message (
    id_message uuid NOT NULL,
    session_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    message_order integer NOT NULL,
    sources_json jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: chat_message_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_message_feedback (
    id_feedback uuid DEFAULT gen_random_uuid() NOT NULL,
    message_id uuid NOT NULL,
    rating smallint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_chat_message_feedback_rating CHECK ((rating = ANY (ARRAY['-1'::integer, 1])))
);


--
-- Name: chat_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_session (
    id_session uuid NOT NULL,
    title character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    id_usuario bigint
);


--
-- Name: chunk_documento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chunk_documento (
    id_chunk_documento bigint NOT NULL,
    id_version_documento bigint NOT NULL,
    contenido text NOT NULL,
    numero_chunk integer NOT NULL,
    pagina_inicio integer,
    pagina_fin integer,
    seccion character varying(255),
    subseccion character varying(255),
    articulo_numero character varying(50),
    estrategia_chunking character varying(100),
    tokens_aproximados integer,
    embedding public.vector(512),
    activo boolean DEFAULT true NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: chunk_documento_id_chunk_documento_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chunk_documento_id_chunk_documento_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chunk_documento_id_chunk_documento_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chunk_documento_id_chunk_documento_seq OWNED BY public.chunk_documento.id_chunk_documento;


--
-- Name: documento_institucional; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_institucional (
    id_documento_institucional bigint NOT NULL,
    titulo character varying(255) NOT NULL,
    tipo_documento character varying(100) NOT NULL,
    descripcion text,
    unidad_origen character varying(150) NOT NULL,
    estado character varying(30) DEFAULT 'activo'::character varying NOT NULL,
    fecha_publicacion date,
    fecha_carga timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    hash_archivo character varying(255) NOT NULL,
    id_version_actual bigint,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: documento_institucional_id_documento_institucional_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_institucional_id_documento_institucional_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_institucional_id_documento_institucional_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_institucional_id_documento_institucional_seq OWNED BY public.documento_institucional.id_documento_institucional;


--
-- Name: evento_autenticacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evento_autenticacion (
    id_evento_autenticacion bigint NOT NULL,
    id_usuario bigint,
    correo_intentado public.citext,
    tipo_evento character varying(40) NOT NULL,
    exitoso boolean NOT NULL,
    motivo_fallo character varying(100),
    direccion_ip inet,
    user_agent text,
    fecha_evento timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_evento_autenticacion_tipo CHECK (((tipo_evento)::text = ANY ((ARRAY['registro'::character varying, 'verificacion_correo'::character varying, 'inicio_sesion'::character varying, 'renovacion_sesion'::character varying, 'cierre_sesion'::character varying, 'solicitud_recuperacion'::character varying, 'cambio_contrasena'::character varying, 'cambio_correo'::character varying, 'bloqueo_cuenta'::character varying, 'desbloqueo_cuenta'::character varying])::text[])))
);


--
-- Name: evento_autenticacion_id_evento_autenticacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evento_autenticacion_id_evento_autenticacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evento_autenticacion_id_evento_autenticacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evento_autenticacion_id_evento_autenticacion_seq OWNED BY public.evento_autenticacion.id_evento_autenticacion;


--
-- Name: perfil_academico; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.perfil_academico (
    id_perfil bigint NOT NULL,
    id_usuario bigint NOT NULL,
    codigo_estudiante character varying(50),
    sede character varying(100),
    carrera_programa character varying(200),
    nivel_academico character varying(100),
    documento_identidad character varying(50),
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_perfil_academico_carrera_programa CHECK (((carrera_programa IS NULL) OR (length(TRIM(BOTH FROM carrera_programa)) >= 2))),
    CONSTRAINT ck_perfil_academico_codigo_estudiante CHECK (((codigo_estudiante IS NULL) OR (length(TRIM(BOTH FROM codigo_estudiante)) >= 1))),
    CONSTRAINT ck_perfil_academico_documento_identidad CHECK (((documento_identidad IS NULL) OR (length(TRIM(BOTH FROM documento_identidad)) >= 3))),
    CONSTRAINT ck_perfil_academico_nivel_academico CHECK (((nivel_academico IS NULL) OR (length(TRIM(BOTH FROM nivel_academico)) >= 2))),
    CONSTRAINT ck_perfil_academico_sede CHECK (((sede IS NULL) OR (length(TRIM(BOTH FROM sede)) >= 2)))
);


--
-- Name: perfil_academico_id_perfil_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.perfil_academico_id_perfil_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: perfil_academico_id_perfil_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.perfil_academico_id_perfil_seq OWNED BY public.perfil_academico.id_perfil;


--
-- Name: rol; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol (
    id_rol bigint NOT NULL,
    nombre character varying(50) NOT NULL,
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_rol_nombre_no_vacio CHECK ((length(TRIM(BOTH FROM nombre)) >= 3))
);


--
-- Name: rol_id_rol_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rol_id_rol_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rol_id_rol_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rol_id_rol_seq OWNED BY public.rol.id_rol;


--
-- Name: sesion_usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sesion_usuario (
    id_sesion bigint NOT NULL,
    id_usuario bigint NOT NULL,
    identificador_sesion uuid DEFAULT gen_random_uuid() NOT NULL,
    refresh_token_hash character varying(64) NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_ultima_actividad timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_expiracion timestamp with time zone NOT NULL,
    fecha_revocacion timestamp with time zone,
    motivo_revocacion character varying(100),
    direccion_ip inet,
    user_agent text,
    CONSTRAINT ck_sesion_expiracion CHECK ((fecha_expiracion > fecha_creacion)),
    CONSTRAINT ck_sesion_revocacion CHECK (((fecha_revocacion IS NULL) OR (fecha_revocacion >= fecha_creacion)))
);


--
-- Name: sesion_usuario_id_sesion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sesion_usuario_id_sesion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sesion_usuario_id_sesion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sesion_usuario_id_sesion_seq OWNED BY public.sesion_usuario.id_sesion;


--
-- Name: solicitud; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud (
    id_solicitud bigint NOT NULL,
    id_solicitante bigint NOT NULL,
    id_tramite bigint NOT NULL,
    estado character varying(30) NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_envio timestamp with time zone,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    nombre_tramite_snapshot character varying(200),
    tipo_finalizacion character varying(30),
    nombre_contacto character varying(200),
    telefono_contacto character varying(30),
    correo_contacto character varying(254),
    tipo_intervencion character varying(20) DEFAULT 'ninguna'::character varying NOT NULL,
    CONSTRAINT ck_solicitud_correo_contacto CHECK (((correo_contacto IS NULL) OR (length(TRIM(BOTH FROM correo_contacto)) >= 5))),
    CONSTRAINT ck_solicitud_estado CHECK (((estado)::text = ANY ((ARRAY['pendiente_recepcion'::character varying, 'en_revision'::character varying, 'en_proceso'::character varying, 'lista_para_entrega'::character varying, 'finalizada'::character varying, 'cancelada'::character varying, 'rechazada'::character varying])::text[]))),
    CONSTRAINT ck_solicitud_fecha_envio CHECK ((((estado)::text = 'cancelada'::text) OR (fecha_envio IS NOT NULL))),
    CONSTRAINT ck_solicitud_fecha_envio_cronologia CHECK (((fecha_envio IS NULL) OR (fecha_envio >= fecha_creacion))),
    CONSTRAINT ck_solicitud_nombre_contacto CHECK (((nombre_contacto IS NULL) OR (length(TRIM(BOTH FROM nombre_contacto)) >= 2))),
    CONSTRAINT ck_solicitud_telefono_contacto CHECK (((telefono_contacto IS NULL) OR (length(TRIM(BOTH FROM telefono_contacto)) >= 7))),
    CONSTRAINT ck_solicitud_tipo_finalizacion CHECK (((tipo_finalizacion)::text = ANY ((ARRAY['entrega'::character varying, 'resultado_registrado'::character varying, 'externo'::character varying])::text[]))),
    CONSTRAINT ck_solicitud_tipo_intervencion CHECK (((tipo_intervencion)::text = ANY ((ARRAY['ninguna'::character varying, 'firma'::character varying, 'conformidad'::character varying])::text[])))
);


--
-- Name: solicitud_dato; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_dato (
    id_solicitud_dato bigint NOT NULL,
    id_solicitud bigint NOT NULL,
    id_campo bigint NOT NULL,
    valor jsonb NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    clave_snapshot character varying(100),
    etiqueta_snapshot character varying(200),
    CONSTRAINT ck_solicitud_dato_valor CHECK ((valor <> 'null'::jsonb))
);


--
-- Name: solicitud_dato_id_solicitud_dato_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_dato_id_solicitud_dato_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_dato_id_solicitud_dato_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_dato_id_solicitud_dato_seq OWNED BY public.solicitud_dato.id_solicitud_dato;


--
-- Name: solicitud_historial; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_historial (
    id_historial bigint NOT NULL,
    id_solicitud bigint NOT NULL,
    id_usuario_actor bigint,
    id_solicitud_requisito bigint,
    evento character varying(80) NOT NULL,
    detalle text NOT NULL,
    visible_solicitante boolean DEFAULT true NOT NULL,
    fecha_evento timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_solicitud_historial_texto CHECK (((length(TRIM(BOTH FROM evento)) > 0) AND (length(TRIM(BOTH FROM detalle)) > 0)))
);


--
-- Name: solicitud_historial_id_historial_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_historial_id_historial_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_historial_id_historial_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_historial_id_historial_seq OWNED BY public.solicitud_historial.id_historial;


--
-- Name: solicitud_id_solicitud_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_id_solicitud_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_id_solicitud_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_id_solicitud_seq OWNED BY public.solicitud.id_solicitud;


--
-- Name: solicitud_intervencion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_intervencion (
    id_intervencion bigint NOT NULL,
    id_solicitud bigint NOT NULL,
    tipo character varying(20) NOT NULL,
    estado character varying(20) DEFAULT 'convocada'::character varying NOT NULL,
    id_usuario_convocatoria bigint NOT NULL,
    fecha_convocatoria timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_revision date,
    id_usuario_registro bigint,
    fecha_registro timestamp with time zone,
    motivo_desacuerdo text,
    CONSTRAINT ck_intervencion_fecha_registro CHECK (((fecha_registro IS NULL) OR (fecha_registro >= fecha_convocatoria))),
    CONSTRAINT ck_intervencion_motivo CHECK (((((estado)::text = 'no_conforme'::text) AND (motivo_desacuerdo IS NOT NULL) AND (length(TRIM(BOTH FROM motivo_desacuerdo)) > 0)) OR (((estado)::text <> 'no_conforme'::text) AND (motivo_desacuerdo IS NULL)))),
    CONSTRAINT ck_intervencion_registro CHECK (((((estado)::text = 'convocada'::text) AND (fecha_revision IS NULL) AND (id_usuario_registro IS NULL) AND (fecha_registro IS NULL)) OR (((estado)::text = ANY ((ARRAY['conforme'::character varying, 'no_conforme'::character varying, 'firmada'::character varying])::text[])) AND (fecha_revision IS NOT NULL) AND (id_usuario_registro IS NOT NULL) AND (fecha_registro IS NOT NULL)) OR (((estado)::text = 'anulada'::text) AND (fecha_revision IS NULL) AND (id_usuario_registro IS NOT NULL) AND (fecha_registro IS NOT NULL)))),
    CONSTRAINT ck_intervencion_tipo_estado CHECK (((((tipo)::text = 'conformidad'::text) AND ((estado)::text = ANY ((ARRAY['convocada'::character varying, 'conforme'::character varying, 'no_conforme'::character varying, 'anulada'::character varying])::text[]))) OR (((tipo)::text = 'firma'::text) AND ((estado)::text = ANY ((ARRAY['convocada'::character varying, 'firmada'::character varying, 'anulada'::character varying])::text[])))))
);


--
-- Name: solicitud_intervencion_id_intervencion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.solicitud_intervencion ALTER COLUMN id_intervencion ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.solicitud_intervencion_id_intervencion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: solicitud_notificacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_notificacion (
    id_notificacion bigint NOT NULL,
    id_solicitud bigint NOT NULL,
    id_intervencion bigint,
    tipo character varying(20) NOT NULL,
    estado character varying(20) DEFAULT 'pendiente'::character varying NOT NULL,
    destinatario character varying(254) NOT NULL,
    asunto character varying(300) NOT NULL,
    contenido_texto text NOT NULL,
    intentos integer DEFAULT 0 NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_ultimo_intento timestamp with time zone,
    fecha_envio timestamp with time zone,
    ultimo_error text,
    referencia_externa character varying(200),
    id_observacion bigint,
    CONSTRAINT ck_notificacion_estado CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'enviado'::character varying, 'fallido'::character varying])::text[]))),
    CONSTRAINT ck_notificacion_fecha_envio CHECK (((((estado)::text = 'enviado'::text) AND (fecha_envio IS NOT NULL)) OR (((estado)::text <> 'enviado'::text) AND (fecha_envio IS NULL)))),
    CONSTRAINT ck_notificacion_intentos CHECK ((intentos >= 0)),
    CONSTRAINT ck_notificacion_texto CHECK (((length(TRIM(BOTH FROM destinatario)) > 0) AND (length(TRIM(BOTH FROM asunto)) > 0) AND (length(TRIM(BOTH FROM contenido_texto)) > 0))),
    CONSTRAINT ck_notificacion_tipo CHECK (((tipo)::text = ANY ((ARRAY['convocatoria'::character varying, 'resultado'::character varying, 'observacion'::character varying])::text[]))),
    CONSTRAINT ck_notificacion_tipo_intervencion CHECK (((((tipo)::text = 'convocatoria'::text) AND (id_intervencion IS NOT NULL) AND (id_observacion IS NULL)) OR (((tipo)::text = 'resultado'::text) AND (id_intervencion IS NULL) AND (id_observacion IS NULL)) OR (((tipo)::text = 'observacion'::text) AND (id_intervencion IS NULL) AND (id_observacion IS NOT NULL))))
);


--
-- Name: solicitud_notificacion_id_notificacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.solicitud_notificacion ALTER COLUMN id_notificacion ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.solicitud_notificacion_id_notificacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: solicitud_observacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_observacion (
    id_observacion bigint NOT NULL,
    id_solicitud bigint NOT NULL,
    id_solicitud_requisito bigint,
    id_usuario_observador bigint NOT NULL,
    detalle text NOT NULL,
    estado character varying(20) DEFAULT 'pendiente'::character varying NOT NULL,
    fecha_observacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    id_usuario_resolucion bigint,
    fecha_resolucion timestamp with time zone,
    CONSTRAINT ck_observacion_resolucion CHECK (((((estado)::text = 'pendiente'::text) AND (id_usuario_resolucion IS NULL) AND (fecha_resolucion IS NULL)) OR (((estado)::text = 'resuelta'::text) AND (id_usuario_resolucion IS NOT NULL) AND (fecha_resolucion IS NOT NULL) AND (fecha_resolucion >= fecha_observacion)))),
    CONSTRAINT ck_observacion_texto CHECK ((length(btrim(detalle)) > 0))
);


--
-- Name: solicitud_observacion_id_observacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_observacion_id_observacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_observacion_id_observacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_observacion_id_observacion_seq OWNED BY public.solicitud_observacion.id_observacion;


--
-- Name: solicitud_pago_verificacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_pago_verificacion (
    id_verificacion_pago bigint NOT NULL,
    id_solicitud_requisito bigint NOT NULL,
    id_usuario_verificador bigint NOT NULL,
    numero_factura_consultado character varying(150) NOT NULL,
    codigo_concepto_consultado character varying(100) NOT NULL,
    codigo_concepto_reportado character varying(100),
    estado_factura_reportado character varying(50),
    monto_reportado numeric(12,2),
    moneda_reportada character varying(3),
    estado character varying(30) NOT NULL,
    detalle_respuesta jsonb,
    fecha_verificacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_pago_verificacion_codigo_consultado CHECK ((length(TRIM(BOTH FROM codigo_concepto_consultado)) >= 1)),
    CONSTRAINT ck_pago_verificacion_codigo_reportado CHECK (((codigo_concepto_reportado IS NULL) OR (length(TRIM(BOTH FROM codigo_concepto_reportado)) >= 1))),
    CONSTRAINT ck_pago_verificacion_estado CHECK (((estado)::text = ANY ((ARRAY['verificado'::character varying, 'no_verificado'::character varying, 'error'::character varying])::text[]))),
    CONSTRAINT ck_pago_verificacion_estado_factura_reportado CHECK (((estado_factura_reportado IS NULL) OR (length(TRIM(BOTH FROM estado_factura_reportado)) >= 1))),
    CONSTRAINT ck_pago_verificacion_moneda CHECK (((moneda_reportada IS NULL) OR (length(TRIM(BOTH FROM moneda_reportada)) = 3))),
    CONSTRAINT ck_pago_verificacion_monto CHECK (((monto_reportado IS NULL) OR (monto_reportado > (0)::numeric))),
    CONSTRAINT ck_pago_verificacion_numero_factura CHECK ((length(TRIM(BOTH FROM numero_factura_consultado)) >= 1))
);


--
-- Name: solicitud_pago_verificacion_id_verificacion_pago_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_pago_verificacion_id_verificacion_pago_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_pago_verificacion_id_verificacion_pago_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_pago_verificacion_id_verificacion_pago_seq OWNED BY public.solicitud_pago_verificacion.id_verificacion_pago;


--
-- Name: solicitud_recepcion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_recepcion (
    id_recepcion bigint NOT NULL,
    id_solicitud bigint NOT NULL,
    id_usuario_receptor bigint NOT NULL,
    fecha_recepcion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: solicitud_recepcion_id_recepcion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_recepcion_id_recepcion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_recepcion_id_recepcion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_recepcion_id_recepcion_seq OWNED BY public.solicitud_recepcion.id_recepcion;


--
-- Name: solicitud_requisito; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_requisito (
    id_solicitud_requisito bigint NOT NULL,
    id_solicitud bigint NOT NULL,
    id_requisito_origen bigint,
    nombre character varying(200) NOT NULL,
    descripcion text,
    obligatorio boolean NOT NULL,
    orden integer NOT NULL,
    id_requisito_economico_origen bigint,
    concepto_economico character varying(200),
    monto_economico numeric(12,2),
    moneda character varying(3),
    gestion smallint,
    codigo_concepto_externo character varying(100),
    numero_factura character varying(150),
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    estado_verificacion character varying(20) DEFAULT 'pendiente'::character varying NOT NULL,
    id_usuario_verificador bigint,
    fecha_verificacion timestamp with time zone,
    detalle_verificacion text,
    requiere_presentacion_fisica boolean DEFAULT false NOT NULL,
    presentado boolean DEFAULT false NOT NULL,
    fecha_presentacion timestamp with time zone,
    id_usuario_presentacion bigint,
    condicion_snapshot jsonb,
    CONSTRAINT ck_solicitud_requisito_concepto_economico CHECK (((concepto_economico IS NULL) OR (length(TRIM(BOTH FROM concepto_economico)) >= 2))),
    CONSTRAINT ck_solicitud_requisito_detalle_verificacion CHECK (((detalle_verificacion IS NULL) OR (length(TRIM(BOTH FROM detalle_verificacion)) >= 1))),
    CONSTRAINT ck_solicitud_requisito_economico CHECK ((((concepto_economico IS NULL) AND (monto_economico IS NULL) AND (moneda IS NULL) AND (gestion IS NULL) AND (codigo_concepto_externo IS NULL)) OR ((concepto_economico IS NOT NULL) AND (monto_economico IS NOT NULL) AND (moneda IS NOT NULL) AND (gestion IS NOT NULL)))),
    CONSTRAINT ck_solicitud_requisito_estado_verificacion CHECK (((estado_verificacion)::text = ANY ((ARRAY['pendiente'::character varying, 'cumple'::character varying, 'no_cumple'::character varying])::text[]))),
    CONSTRAINT ck_solicitud_requisito_gestion CHECK (((gestion IS NULL) OR ((gestion >= 2000) AND (gestion <= 2100)))),
    CONSTRAINT ck_solicitud_requisito_moneda CHECK (((moneda IS NULL) OR (length(TRIM(BOTH FROM moneda)) = 3))),
    CONSTRAINT ck_solicitud_requisito_monto_economico CHECK (((monto_economico IS NULL) OR (monto_economico > (0)::numeric))),
    CONSTRAINT ck_solicitud_requisito_nombre CHECK ((length(TRIM(BOTH FROM nombre)) >= 2)),
    CONSTRAINT ck_solicitud_requisito_numero_factura CHECK (((numero_factura IS NULL) OR (length(TRIM(BOTH FROM numero_factura)) >= 1))),
    CONSTRAINT ck_solicitud_requisito_orden CHECK ((orden > 0)),
    CONSTRAINT ck_solicitud_requisito_presentacion CHECK ((((NOT presentado) AND (fecha_presentacion IS NULL) AND (id_usuario_presentacion IS NULL)) OR (presentado AND requiere_presentacion_fisica AND (fecha_presentacion IS NOT NULL) AND (id_usuario_presentacion IS NOT NULL) AND (fecha_presentacion >= fecha_creacion)))),
    CONSTRAINT ck_solicitud_requisito_verificacion_consistente CHECK (((((estado_verificacion)::text = 'pendiente'::text) AND (id_usuario_verificador IS NULL) AND (fecha_verificacion IS NULL)) OR (((estado_verificacion)::text = ANY ((ARRAY['cumple'::character varying, 'no_cumple'::character varying])::text[])) AND (id_usuario_verificador IS NOT NULL) AND (fecha_verificacion IS NOT NULL))))
);


--
-- Name: solicitud_requisito_id_solicitud_requisito_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_requisito_id_solicitud_requisito_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_requisito_id_solicitud_requisito_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_requisito_id_solicitud_requisito_seq OWNED BY public.solicitud_requisito.id_solicitud_requisito;


--
-- Name: solicitud_resultado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_resultado (
    id_resultado bigint NOT NULL,
    id_solicitud bigint NOT NULL,
    tipo_finalizacion character varying(30) NOT NULL,
    detalle text,
    id_usuario_registro bigint NOT NULL,
    fecha_registro timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT solicitud_resultado_tipo_finalizacion_check CHECK (((tipo_finalizacion)::text = ANY ((ARRAY['entrega'::character varying, 'resultado_registrado'::character varying, 'externo'::character varying])::text[])))
);


--
-- Name: solicitud_resultado_id_resultado_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_resultado_id_resultado_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_resultado_id_resultado_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_resultado_id_resultado_seq OWNED BY public.solicitud_resultado.id_resultado;


--
-- Name: token_recuperacion_contrasena; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.token_recuperacion_contrasena (
    id_token_recuperacion bigint NOT NULL,
    id_usuario bigint NOT NULL,
    token_hash character varying(64) NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_expiracion timestamp with time zone NOT NULL,
    fecha_utilizacion timestamp with time zone,
    fecha_revocacion timestamp with time zone,
    direccion_ip_solicitud inet,
    CONSTRAINT ck_token_recuperacion_expiracion CHECK ((fecha_expiracion > fecha_creacion)),
    CONSTRAINT ck_token_recuperacion_revocacion CHECK (((fecha_revocacion IS NULL) OR (fecha_revocacion >= fecha_creacion))),
    CONSTRAINT ck_token_recuperacion_utilizacion CHECK (((fecha_utilizacion IS NULL) OR (fecha_utilizacion >= fecha_creacion)))
);


--
-- Name: token_recuperacion_contrasena_id_token_recuperacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.token_recuperacion_contrasena_id_token_recuperacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: token_recuperacion_contrasena_id_token_recuperacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.token_recuperacion_contrasena_id_token_recuperacion_seq OWNED BY public.token_recuperacion_contrasena.id_token_recuperacion;


--
-- Name: token_verificacion_correo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.token_verificacion_correo (
    id_token_verificacion bigint NOT NULL,
    id_usuario_correo bigint NOT NULL,
    token_hash character varying(64) NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_expiracion timestamp with time zone NOT NULL,
    fecha_utilizacion timestamp with time zone,
    fecha_revocacion timestamp with time zone,
    direccion_ip_solicitud inet,
    CONSTRAINT ck_token_verificacion_expiracion CHECK ((fecha_expiracion > fecha_creacion)),
    CONSTRAINT ck_token_verificacion_revocacion CHECK (((fecha_revocacion IS NULL) OR (fecha_revocacion >= fecha_creacion))),
    CONSTRAINT ck_token_verificacion_utilizacion CHECK (((fecha_utilizacion IS NULL) OR (fecha_utilizacion >= fecha_creacion)))
);


--
-- Name: token_verificacion_correo_id_token_verificacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.token_verificacion_correo_id_token_verificacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: token_verificacion_correo_id_token_verificacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.token_verificacion_correo_id_token_verificacion_seq OWNED BY public.token_verificacion_correo.id_token_verificacion;


--
-- Name: tramite; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tramite (
    id_tramite bigint NOT NULL,
    nombre character varying(200) NOT NULL,
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    publicado boolean DEFAULT false NOT NULL,
    permite_solicitudes boolean DEFAULT false NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    tiempo_estimado text,
    canales_atencion text,
    instrucciones text,
    condiciones text,
    tipo_finalizacion character varying(30),
    tipo_intervencion character varying(20) DEFAULT 'ninguna'::character varying NOT NULL,
    CONSTRAINT ck_tramite_nombre_no_vacio CHECK ((length(TRIM(BOTH FROM nombre)) >= 3)),
    CONSTRAINT ck_tramite_permite_solicitudes CHECK (((permite_solicitudes = false) OR ((activo = true) AND (publicado = true)))),
    CONSTRAINT ck_tramite_publicacion CHECK (((publicado = false) OR (activo = true))),
    CONSTRAINT ck_tramite_tipo_finalizacion CHECK (((tipo_finalizacion)::text = ANY ((ARRAY['entrega'::character varying, 'resultado_registrado'::character varying, 'externo'::character varying])::text[]))),
    CONSTRAINT ck_tramite_tipo_intervencion CHECK (((tipo_intervencion)::text = ANY ((ARRAY['ninguna'::character varying, 'firma'::character varying, 'conformidad'::character varying])::text[])))
);


--
-- Name: tramite_campo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tramite_campo (
    id_campo bigint NOT NULL,
    id_tramite bigint NOT NULL,
    clave character varying(80) NOT NULL,
    etiqueta character varying(150) NOT NULL,
    descripcion text,
    tipo_dato character varying(30) NOT NULL,
    obligatorio boolean DEFAULT false NOT NULL,
    orden integer DEFAULT 1 NOT NULL,
    configuracion jsonb,
    activo boolean DEFAULT true NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_tramite_campo_clave_no_vacia CHECK ((length(TRIM(BOTH FROM clave)) >= 2)),
    CONSTRAINT ck_tramite_campo_etiqueta_no_vacia CHECK ((length(TRIM(BOTH FROM etiqueta)) >= 2)),
    CONSTRAINT ck_tramite_campo_orden CHECK ((orden > 0)),
    CONSTRAINT ck_tramite_campo_tipo_dato CHECK (((tipo_dato)::text = ANY ((ARRAY['texto'::character varying, 'texto_largo'::character varying, 'entero'::character varying, 'decimal'::character varying, 'fecha'::character varying, 'booleano'::character varying, 'seleccion'::character varying])::text[])))
);


--
-- Name: tramite_campo_id_campo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tramite_campo_id_campo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tramite_campo_id_campo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tramite_campo_id_campo_seq OWNED BY public.tramite_campo.id_campo;


--
-- Name: tramite_id_tramite_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tramite_id_tramite_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tramite_id_tramite_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tramite_id_tramite_seq OWNED BY public.tramite.id_tramite;


--
-- Name: tramite_requisito; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tramite_requisito (
    id_requisito bigint NOT NULL,
    id_tramite bigint NOT NULL,
    nombre character varying(200) NOT NULL,
    descripcion text,
    obligatorio boolean DEFAULT true NOT NULL,
    orden integer DEFAULT 1 NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    requiere_presentacion_fisica boolean DEFAULT false NOT NULL,
    condicion jsonb,
    CONSTRAINT ck_tramite_requisito_condicion CHECK (((condicion IS NULL) OR ((jsonb_typeof(condicion) = 'object'::text) AND ((condicion ->> 'operador'::text) = ANY (ARRAY['igual'::text, 'distinto'::text])) AND ((condicion ->> 'origen'::text) = ANY (ARRAY['solicitud_dato'::text, 'perfil_academico'::text]))))),
    CONSTRAINT ck_tramite_requisito_nombre_no_vacio CHECK ((length(TRIM(BOTH FROM nombre)) >= 2)),
    CONSTRAINT ck_tramite_requisito_orden CHECK ((orden > 0))
);


--
-- Name: tramite_requisito_economico; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tramite_requisito_economico (
    id_requisito_economico bigint NOT NULL,
    id_requisito bigint NOT NULL,
    concepto character varying(200) NOT NULL,
    monto numeric(12,2) NOT NULL,
    moneda character varying(3) DEFAULT 'BOB'::character varying NOT NULL,
    gestion smallint NOT NULL,
    codigo_concepto_externo character varying(100),
    activo boolean DEFAULT true NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_tramite_requisito_economico_concepto CHECK ((length(TRIM(BOTH FROM concepto)) >= 2)),
    CONSTRAINT ck_tramite_requisito_economico_gestion CHECK (((gestion >= 2000) AND (gestion <= 2100))),
    CONSTRAINT ck_tramite_requisito_economico_moneda CHECK ((length(TRIM(BOTH FROM moneda)) = 3)),
    CONSTRAINT ck_tramite_requisito_economico_monto CHECK ((monto > (0)::numeric))
);


--
-- Name: tramite_requisito_economico_id_requisito_economico_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tramite_requisito_economico_id_requisito_economico_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tramite_requisito_economico_id_requisito_economico_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tramite_requisito_economico_id_requisito_economico_seq OWNED BY public.tramite_requisito_economico.id_requisito_economico;


--
-- Name: tramite_requisito_id_requisito_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tramite_requisito_id_requisito_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tramite_requisito_id_requisito_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tramite_requisito_id_requisito_seq OWNED BY public.tramite_requisito.id_requisito;


--
-- Name: unidad_administrativa; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.unidad_administrativa (
    id_unidad bigint NOT NULL,
    nombre character varying(120) NOT NULL,
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_unidad_administrativa_nombre_no_vacio CHECK ((length(TRIM(BOTH FROM nombre)) >= 3))
);


--
-- Name: unidad_administrativa_id_unidad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.unidad_administrativa_id_unidad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: unidad_administrativa_id_unidad_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.unidad_administrativa_id_unidad_seq OWNED BY public.unidad_administrativa.id_unidad;


--
-- Name: usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario (
    id_usuario bigint NOT NULL,
    nombres character varying(100) NOT NULL,
    apellidos character varying(100) NOT NULL,
    contrasena_hash text,
    estado character varying(30) DEFAULT 'pendiente_verificacion'::character varying NOT NULL,
    fecha_ultimo_acceso timestamp with time zone,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    telefono character varying(30),
    CONSTRAINT ck_usuario_apellidos_no_vacios CHECK ((length(TRIM(BOTH FROM apellidos)) >= 2)),
    CONSTRAINT ck_usuario_estado CHECK (((estado)::text = ANY ((ARRAY['pendiente_verificacion'::character varying, 'activo'::character varying, 'bloqueado'::character varying, 'inactivo'::character varying])::text[]))),
    CONSTRAINT ck_usuario_nombres_no_vacios CHECK ((length(TRIM(BOTH FROM nombres)) >= 2)),
    CONSTRAINT ck_usuario_telefono CHECK (((telefono IS NULL) OR (length(TRIM(BOTH FROM telefono)) >= 7)))
);


--
-- Name: usuario_correo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_correo (
    id_usuario_correo bigint NOT NULL,
    id_usuario bigint NOT NULL,
    correo public.citext NOT NULL,
    tipo character varying(20) NOT NULL,
    es_principal boolean DEFAULT false NOT NULL,
    verificado boolean DEFAULT false NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    fecha_verificacion timestamp with time zone,
    fecha_creacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_actualizacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_usuario_correo_tipo CHECK (((tipo)::text = ANY ((ARRAY['institucional'::character varying, 'personal'::character varying])::text[]))),
    CONSTRAINT ck_usuario_correo_verificacion CHECK ((((verificado = false) AND (fecha_verificacion IS NULL)) OR ((verificado = true) AND (fecha_verificacion IS NOT NULL))))
);


--
-- Name: usuario_correo_id_usuario_correo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_correo_id_usuario_correo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_correo_id_usuario_correo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_correo_id_usuario_correo_seq OWNED BY public.usuario_correo.id_usuario_correo;


--
-- Name: usuario_id_usuario_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_id_usuario_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_id_usuario_seq OWNED BY public.usuario.id_usuario;


--
-- Name: usuario_identidad_externa; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_identidad_externa (
    id_usuario_identidad bigint NOT NULL,
    id_usuario bigint NOT NULL,
    proveedor character varying(50) NOT NULL,
    identificador_proveedor character varying(255) NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: usuario_identidad_externa_id_usuario_identidad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_identidad_externa_id_usuario_identidad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_identidad_externa_id_usuario_identidad_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_identidad_externa_id_usuario_identidad_seq OWNED BY public.usuario_identidad_externa.id_usuario_identidad;


--
-- Name: usuario_rol; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_rol (
    id_usuario_rol bigint NOT NULL,
    id_usuario bigint NOT NULL,
    id_rol bigint NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    asignado_por bigint,
    fecha_asignacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_revocacion timestamp with time zone,
    CONSTRAINT ck_usuario_rol_revocacion CHECK ((((activo = true) AND (fecha_revocacion IS NULL)) OR (activo = false)))
);


--
-- Name: usuario_rol_id_usuario_rol_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_rol_id_usuario_rol_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_rol_id_usuario_rol_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_rol_id_usuario_rol_seq OWNED BY public.usuario_rol.id_usuario_rol;


--
-- Name: usuario_unidad; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_unidad (
    id_usuario_unidad bigint NOT NULL,
    id_usuario bigint NOT NULL,
    id_unidad bigint NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    asignado_por bigint,
    fecha_asignacion timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_revocacion timestamp with time zone,
    CONSTRAINT ck_usuario_unidad_revocacion CHECK ((((activo = true) AND (fecha_revocacion IS NULL)) OR (activo = false)))
);


--
-- Name: usuario_unidad_id_usuario_unidad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_unidad_id_usuario_unidad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_unidad_id_usuario_unidad_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_unidad_id_usuario_unidad_seq OWNED BY public.usuario_unidad.id_usuario_unidad;


--
-- Name: version_documento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.version_documento (
    id_version_documento bigint NOT NULL,
    id_documento_institucional bigint NOT NULL,
    numero_version character varying(50) NOT NULL,
    fecha_version timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    hash_archivo character varying(255) NOT NULL,
    estado character varying(30) DEFAULT 'activo'::character varying NOT NULL,
    observacion text,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    vigente_desde date,
    vigente_hasta date,
    CONSTRAINT ck_version_documento_vigencia CHECK (((vigente_hasta IS NULL) OR ((vigente_desde IS NOT NULL) AND (vigente_hasta >= vigente_desde))))
);


--
-- Name: version_documento_id_version_documento_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.version_documento_id_version_documento_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: version_documento_id_version_documento_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.version_documento_id_version_documento_seq OWNED BY public.version_documento.id_version_documento;


--
-- Name: auditoria id_auditoria; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria ALTER COLUMN id_auditoria SET DEFAULT nextval('public.auditoria_id_auditoria_seq'::regclass);


--
-- Name: chunk_documento id_chunk_documento; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunk_documento ALTER COLUMN id_chunk_documento SET DEFAULT nextval('public.chunk_documento_id_chunk_documento_seq'::regclass);


--
-- Name: documento_institucional id_documento_institucional; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_institucional ALTER COLUMN id_documento_institucional SET DEFAULT nextval('public.documento_institucional_id_documento_institucional_seq'::regclass);


--
-- Name: evento_autenticacion id_evento_autenticacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_autenticacion ALTER COLUMN id_evento_autenticacion SET DEFAULT nextval('public.evento_autenticacion_id_evento_autenticacion_seq'::regclass);


--
-- Name: perfil_academico id_perfil; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_academico ALTER COLUMN id_perfil SET DEFAULT nextval('public.perfil_academico_id_perfil_seq'::regclass);


--
-- Name: rol id_rol; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol ALTER COLUMN id_rol SET DEFAULT nextval('public.rol_id_rol_seq'::regclass);


--
-- Name: sesion_usuario id_sesion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario ALTER COLUMN id_sesion SET DEFAULT nextval('public.sesion_usuario_id_sesion_seq'::regclass);


--
-- Name: solicitud id_solicitud; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud ALTER COLUMN id_solicitud SET DEFAULT nextval('public.solicitud_id_solicitud_seq'::regclass);


--
-- Name: solicitud_dato id_solicitud_dato; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_dato ALTER COLUMN id_solicitud_dato SET DEFAULT nextval('public.solicitud_dato_id_solicitud_dato_seq'::regclass);


--
-- Name: solicitud_historial id_historial; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_historial ALTER COLUMN id_historial SET DEFAULT nextval('public.solicitud_historial_id_historial_seq'::regclass);


--
-- Name: solicitud_observacion id_observacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_observacion ALTER COLUMN id_observacion SET DEFAULT nextval('public.solicitud_observacion_id_observacion_seq'::regclass);


--
-- Name: solicitud_pago_verificacion id_verificacion_pago; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_pago_verificacion ALTER COLUMN id_verificacion_pago SET DEFAULT nextval('public.solicitud_pago_verificacion_id_verificacion_pago_seq'::regclass);


--
-- Name: solicitud_recepcion id_recepcion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_recepcion ALTER COLUMN id_recepcion SET DEFAULT nextval('public.solicitud_recepcion_id_recepcion_seq'::regclass);


--
-- Name: solicitud_requisito id_solicitud_requisito; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_requisito ALTER COLUMN id_solicitud_requisito SET DEFAULT nextval('public.solicitud_requisito_id_solicitud_requisito_seq'::regclass);


--
-- Name: solicitud_resultado id_resultado; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_resultado ALTER COLUMN id_resultado SET DEFAULT nextval('public.solicitud_resultado_id_resultado_seq'::regclass);


--
-- Name: token_recuperacion_contrasena id_token_recuperacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_recuperacion_contrasena ALTER COLUMN id_token_recuperacion SET DEFAULT nextval('public.token_recuperacion_contrasena_id_token_recuperacion_seq'::regclass);


--
-- Name: token_verificacion_correo id_token_verificacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_verificacion_correo ALTER COLUMN id_token_verificacion SET DEFAULT nextval('public.token_verificacion_correo_id_token_verificacion_seq'::regclass);


--
-- Name: tramite id_tramite; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite ALTER COLUMN id_tramite SET DEFAULT nextval('public.tramite_id_tramite_seq'::regclass);


--
-- Name: tramite_campo id_campo; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_campo ALTER COLUMN id_campo SET DEFAULT nextval('public.tramite_campo_id_campo_seq'::regclass);


--
-- Name: tramite_requisito id_requisito; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_requisito ALTER COLUMN id_requisito SET DEFAULT nextval('public.tramite_requisito_id_requisito_seq'::regclass);


--
-- Name: tramite_requisito_economico id_requisito_economico; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_requisito_economico ALTER COLUMN id_requisito_economico SET DEFAULT nextval('public.tramite_requisito_economico_id_requisito_economico_seq'::regclass);


--
-- Name: unidad_administrativa id_unidad; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_administrativa ALTER COLUMN id_unidad SET DEFAULT nextval('public.unidad_administrativa_id_unidad_seq'::regclass);


--
-- Name: usuario id_usuario; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id_usuario SET DEFAULT nextval('public.usuario_id_usuario_seq'::regclass);


--
-- Name: usuario_correo id_usuario_correo; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_correo ALTER COLUMN id_usuario_correo SET DEFAULT nextval('public.usuario_correo_id_usuario_correo_seq'::regclass);


--
-- Name: usuario_identidad_externa id_usuario_identidad; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_identidad_externa ALTER COLUMN id_usuario_identidad SET DEFAULT nextval('public.usuario_identidad_externa_id_usuario_identidad_seq'::regclass);


--
-- Name: usuario_rol id_usuario_rol; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol ALTER COLUMN id_usuario_rol SET DEFAULT nextval('public.usuario_rol_id_usuario_rol_seq'::regclass);


--
-- Name: usuario_unidad id_usuario_unidad; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_unidad ALTER COLUMN id_usuario_unidad SET DEFAULT nextval('public.usuario_unidad_id_usuario_unidad_seq'::regclass);


--
-- Name: version_documento id_version_documento; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.version_documento ALTER COLUMN id_version_documento SET DEFAULT nextval('public.version_documento_id_version_documento_seq'::regclass);


--
-- Name: auditoria auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT auditoria_pkey PRIMARY KEY (id_auditoria);


--
-- Name: chat_message_feedback chat_message_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_message_feedback
    ADD CONSTRAINT chat_message_feedback_pkey PRIMARY KEY (id_feedback);


--
-- Name: chat_message chat_message_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_message
    ADD CONSTRAINT chat_message_pkey PRIMARY KEY (id_message);


--
-- Name: chat_session chat_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_session
    ADD CONSTRAINT chat_session_pkey PRIMARY KEY (id_session);


--
-- Name: chunk_documento chunk_documento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunk_documento
    ADD CONSTRAINT chunk_documento_pkey PRIMARY KEY (id_chunk_documento);


--
-- Name: documento_institucional documento_institucional_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_institucional
    ADD CONSTRAINT documento_institucional_pkey PRIMARY KEY (id_documento_institucional);


--
-- Name: evento_autenticacion evento_autenticacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_autenticacion
    ADD CONSTRAINT evento_autenticacion_pkey PRIMARY KEY (id_evento_autenticacion);


--
-- Name: perfil_academico perfil_academico_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_academico
    ADD CONSTRAINT perfil_academico_pkey PRIMARY KEY (id_perfil);


--
-- Name: archivo_documento pk_archivo_documento; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archivo_documento
    ADD CONSTRAINT pk_archivo_documento PRIMARY KEY (id_version_documento);


--
-- Name: rol rol_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_pkey PRIMARY KEY (id_rol);


--
-- Name: sesion_usuario sesion_usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT sesion_usuario_pkey PRIMARY KEY (id_sesion);


--
-- Name: solicitud_dato solicitud_dato_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_dato
    ADD CONSTRAINT solicitud_dato_pkey PRIMARY KEY (id_solicitud_dato);


--
-- Name: solicitud_historial solicitud_historial_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_historial
    ADD CONSTRAINT solicitud_historial_pkey PRIMARY KEY (id_historial);


--
-- Name: solicitud_intervencion solicitud_intervencion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_intervencion
    ADD CONSTRAINT solicitud_intervencion_pkey PRIMARY KEY (id_intervencion);


--
-- Name: solicitud_notificacion solicitud_notificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_notificacion
    ADD CONSTRAINT solicitud_notificacion_pkey PRIMARY KEY (id_notificacion);


--
-- Name: solicitud_observacion solicitud_observacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_observacion
    ADD CONSTRAINT solicitud_observacion_pkey PRIMARY KEY (id_observacion);


--
-- Name: solicitud_pago_verificacion solicitud_pago_verificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_pago_verificacion
    ADD CONSTRAINT solicitud_pago_verificacion_pkey PRIMARY KEY (id_verificacion_pago);


--
-- Name: solicitud solicitud_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud
    ADD CONSTRAINT solicitud_pkey PRIMARY KEY (id_solicitud);


--
-- Name: solicitud_recepcion solicitud_recepcion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_recepcion
    ADD CONSTRAINT solicitud_recepcion_pkey PRIMARY KEY (id_recepcion);


--
-- Name: solicitud_requisito solicitud_requisito_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT solicitud_requisito_pkey PRIMARY KEY (id_solicitud_requisito);


--
-- Name: solicitud_resultado solicitud_resultado_id_solicitud_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_resultado
    ADD CONSTRAINT solicitud_resultado_id_solicitud_key UNIQUE (id_solicitud);


--
-- Name: solicitud_resultado solicitud_resultado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_resultado
    ADD CONSTRAINT solicitud_resultado_pkey PRIMARY KEY (id_resultado);


--
-- Name: token_recuperacion_contrasena token_recuperacion_contrasena_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_recuperacion_contrasena
    ADD CONSTRAINT token_recuperacion_contrasena_pkey PRIMARY KEY (id_token_recuperacion);


--
-- Name: token_verificacion_correo token_verificacion_correo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_verificacion_correo
    ADD CONSTRAINT token_verificacion_correo_pkey PRIMARY KEY (id_token_verificacion);


--
-- Name: tramite_campo tramite_campo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_campo
    ADD CONSTRAINT tramite_campo_pkey PRIMARY KEY (id_campo);


--
-- Name: tramite tramite_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite
    ADD CONSTRAINT tramite_pkey PRIMARY KEY (id_tramite);


--
-- Name: tramite_requisito_economico tramite_requisito_economico_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_requisito_economico
    ADD CONSTRAINT tramite_requisito_economico_pkey PRIMARY KEY (id_requisito_economico);


--
-- Name: tramite_requisito tramite_requisito_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_requisito
    ADD CONSTRAINT tramite_requisito_pkey PRIMARY KEY (id_requisito);


--
-- Name: unidad_administrativa unidad_administrativa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_administrativa
    ADD CONSTRAINT unidad_administrativa_pkey PRIMARY KEY (id_unidad);


--
-- Name: chat_message_feedback uq_chat_message_feedback_message; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_message_feedback
    ADD CONSTRAINT uq_chat_message_feedback_message UNIQUE (message_id);


--
-- Name: chunk_documento uq_chunk_numero; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunk_documento
    ADD CONSTRAINT uq_chunk_numero UNIQUE (id_version_documento, numero_chunk);


--
-- Name: usuario_identidad_externa uq_identidad_externa_proveedor_identificador; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_identidad_externa
    ADD CONSTRAINT uq_identidad_externa_proveedor_identificador UNIQUE (proveedor, identificador_proveedor);


--
-- Name: usuario_identidad_externa uq_identidad_externa_usuario_proveedor; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_identidad_externa
    ADD CONSTRAINT uq_identidad_externa_usuario_proveedor UNIQUE (id_usuario, proveedor);


--
-- Name: perfil_academico uq_perfil_academico_usuario; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_academico
    ADD CONSTRAINT uq_perfil_academico_usuario UNIQUE (id_usuario);


--
-- Name: rol uq_rol_nombre; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT uq_rol_nombre UNIQUE (nombre);


--
-- Name: sesion_usuario uq_sesion_identificador; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT uq_sesion_identificador UNIQUE (identificador_sesion);


--
-- Name: sesion_usuario uq_sesion_refresh_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT uq_sesion_refresh_token_hash UNIQUE (refresh_token_hash);


--
-- Name: solicitud_dato uq_solicitud_dato_campo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_dato
    ADD CONSTRAINT uq_solicitud_dato_campo UNIQUE (id_solicitud, id_campo);


--
-- Name: solicitud_recepcion uq_solicitud_recepcion_solicitud; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_recepcion
    ADD CONSTRAINT uq_solicitud_recepcion_solicitud UNIQUE (id_solicitud);


--
-- Name: solicitud_requisito uq_solicitud_requisito_origen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT uq_solicitud_requisito_origen UNIQUE (id_solicitud, id_requisito_origen);


--
-- Name: solicitud_requisito uq_solicitud_requisito_pertenencia; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT uq_solicitud_requisito_pertenencia UNIQUE (id_solicitud, id_solicitud_requisito);


--
-- Name: token_recuperacion_contrasena uq_token_recuperacion_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_recuperacion_contrasena
    ADD CONSTRAINT uq_token_recuperacion_hash UNIQUE (token_hash);


--
-- Name: token_verificacion_correo uq_token_verificacion_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_verificacion_correo
    ADD CONSTRAINT uq_token_verificacion_hash UNIQUE (token_hash);


--
-- Name: tramite_campo uq_tramite_campo_clave; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_campo
    ADD CONSTRAINT uq_tramite_campo_clave UNIQUE (id_tramite, clave);


--
-- Name: tramite uq_tramite_nombre; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite
    ADD CONSTRAINT uq_tramite_nombre UNIQUE (nombre);


--
-- Name: tramite_requisito_economico uq_tramite_requisito_economico_gestion; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_requisito_economico
    ADD CONSTRAINT uq_tramite_requisito_economico_gestion UNIQUE (id_requisito, gestion);


--
-- Name: tramite_requisito uq_tramite_requisito_nombre; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_requisito
    ADD CONSTRAINT uq_tramite_requisito_nombre UNIQUE (id_tramite, nombre);


--
-- Name: unidad_administrativa uq_unidad_administrativa_nombre; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_administrativa
    ADD CONSTRAINT uq_unidad_administrativa_nombre UNIQUE (nombre);


--
-- Name: usuario_correo uq_usuario_correo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_correo
    ADD CONSTRAINT uq_usuario_correo UNIQUE (correo);


--
-- Name: usuario_rol uq_usuario_rol; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol
    ADD CONSTRAINT uq_usuario_rol UNIQUE (id_usuario, id_rol);


--
-- Name: usuario_unidad uq_usuario_unidad; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_unidad
    ADD CONSTRAINT uq_usuario_unidad UNIQUE (id_usuario, id_unidad);


--
-- Name: version_documento uq_version_documento; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.version_documento
    ADD CONSTRAINT uq_version_documento UNIQUE (id_documento_institucional, numero_version);


--
-- Name: usuario_correo usuario_correo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_correo
    ADD CONSTRAINT usuario_correo_pkey PRIMARY KEY (id_usuario_correo);


--
-- Name: usuario_identidad_externa usuario_identidad_externa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_identidad_externa
    ADD CONSTRAINT usuario_identidad_externa_pkey PRIMARY KEY (id_usuario_identidad);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id_usuario);


--
-- Name: usuario_rol usuario_rol_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol
    ADD CONSTRAINT usuario_rol_pkey PRIMARY KEY (id_usuario_rol);


--
-- Name: usuario_unidad usuario_unidad_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_unidad
    ADD CONSTRAINT usuario_unidad_pkey PRIMARY KEY (id_usuario_unidad);


--
-- Name: version_documento version_documento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.version_documento
    ADD CONSTRAINT version_documento_pkey PRIMARY KEY (id_version_documento);


--
-- Name: idx_auditoria_entidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auditoria_entidad ON public.auditoria USING btree (entidad, id_entidad);


--
-- Name: idx_auditoria_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auditoria_fecha ON public.auditoria USING btree (fecha_evento DESC);


--
-- Name: idx_auditoria_modulo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auditoria_modulo ON public.auditoria USING btree (modulo, fecha_evento DESC);


--
-- Name: idx_auditoria_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auditoria_usuario ON public.auditoria USING btree (id_usuario_actor);


--
-- Name: idx_chat_message_feedback_rating; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_chat_message_feedback_rating ON public.chat_message_feedback USING btree (rating);


--
-- Name: idx_chat_message_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_chat_message_session_id ON public.chat_message USING btree (session_id);


--
-- Name: idx_chat_message_session_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_chat_message_session_order ON public.chat_message USING btree (session_id, message_order);


--
-- Name: idx_evento_autenticacion_correo_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evento_autenticacion_correo_fecha ON public.evento_autenticacion USING btree (correo_intentado, fecha_evento DESC);


--
-- Name: idx_evento_autenticacion_fallido; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evento_autenticacion_fallido ON public.evento_autenticacion USING btree (fecha_evento DESC) WHERE (exitoso = false);


--
-- Name: idx_evento_autenticacion_ip_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evento_autenticacion_ip_fecha ON public.evento_autenticacion USING btree (direccion_ip, fecha_evento DESC);


--
-- Name: idx_evento_autenticacion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evento_autenticacion_usuario ON public.evento_autenticacion USING btree (id_usuario);


--
-- Name: idx_identidad_externa_proveedor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_identidad_externa_proveedor ON public.usuario_identidad_externa USING btree (proveedor);


--
-- Name: idx_identidad_externa_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_identidad_externa_usuario ON public.usuario_identidad_externa USING btree (id_usuario);


--
-- Name: idx_intervencion_solicitud; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_intervencion_solicitud ON public.solicitud_intervencion USING btree (id_solicitud, fecha_convocatoria DESC);


--
-- Name: idx_notificacion_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notificacion_estado ON public.solicitud_notificacion USING btree (estado);


--
-- Name: idx_notificacion_solicitud; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notificacion_solicitud ON public.solicitud_notificacion USING btree (id_solicitud, fecha_creacion DESC);


--
-- Name: idx_pago_verificacion_codigo_consultado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pago_verificacion_codigo_consultado ON public.solicitud_pago_verificacion USING btree (codigo_concepto_consultado);


--
-- Name: idx_pago_verificacion_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pago_verificacion_estado ON public.solicitud_pago_verificacion USING btree (estado);


--
-- Name: idx_pago_verificacion_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pago_verificacion_fecha ON public.solicitud_pago_verificacion USING btree (fecha_verificacion DESC);


--
-- Name: idx_pago_verificacion_numero_factura; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pago_verificacion_numero_factura ON public.solicitud_pago_verificacion USING btree (numero_factura_consultado);


--
-- Name: idx_pago_verificacion_requisito; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pago_verificacion_requisito ON public.solicitud_pago_verificacion USING btree (id_solicitud_requisito);


--
-- Name: idx_pago_verificacion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pago_verificacion_usuario ON public.solicitud_pago_verificacion USING btree (id_usuario_verificador);


--
-- Name: idx_perfil_academico_codigo_estudiante; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_perfil_academico_codigo_estudiante ON public.perfil_academico USING btree (codigo_estudiante) WHERE (codigo_estudiante IS NOT NULL);


--
-- Name: idx_perfil_academico_documento_identidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_perfil_academico_documento_identidad ON public.perfil_academico USING btree (documento_identidad) WHERE (documento_identidad IS NOT NULL);


--
-- Name: idx_sesion_expiracion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sesion_expiracion ON public.sesion_usuario USING btree (fecha_expiracion);


--
-- Name: idx_sesion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sesion_usuario ON public.sesion_usuario USING btree (id_usuario);


--
-- Name: idx_sesion_usuario_vigente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sesion_usuario_vigente ON public.sesion_usuario USING btree (id_usuario, fecha_expiracion) WHERE (fecha_revocacion IS NULL);


--
-- Name: idx_solicitud_dato_campo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_dato_campo ON public.solicitud_dato USING btree (id_campo);


--
-- Name: idx_solicitud_dato_solicitud; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_dato_solicitud ON public.solicitud_dato USING btree (id_solicitud);


--
-- Name: idx_solicitud_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_estado ON public.solicitud USING btree (estado);


--
-- Name: idx_solicitud_fecha_creacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_fecha_creacion ON public.solicitud USING btree (fecha_creacion DESC);


--
-- Name: idx_solicitud_fecha_envio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_fecha_envio ON public.solicitud USING btree (fecha_envio, id_solicitud) WHERE (fecha_envio IS NOT NULL);


--
-- Name: idx_solicitud_historial_cronologia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_historial_cronologia ON public.solicitud_historial USING btree (id_solicitud, fecha_evento, id_historial);


--
-- Name: idx_solicitud_observacion_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_observacion_estado ON public.solicitud_observacion USING btree (id_solicitud, estado);


--
-- Name: idx_solicitud_recepcion_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_recepcion_fecha ON public.solicitud_recepcion USING btree (fecha_recepcion DESC);


--
-- Name: idx_solicitud_recepcion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_recepcion_usuario ON public.solicitud_recepcion USING btree (id_usuario_receptor);


--
-- Name: idx_solicitud_requisito_economico_origen; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_requisito_economico_origen ON public.solicitud_requisito USING btree (id_requisito_economico_origen) WHERE (id_requisito_economico_origen IS NOT NULL);


--
-- Name: idx_solicitud_requisito_estado_verificacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_requisito_estado_verificacion ON public.solicitud_requisito USING btree (id_solicitud, estado_verificacion);


--
-- Name: idx_solicitud_requisito_numero_factura; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_requisito_numero_factura ON public.solicitud_requisito USING btree (numero_factura) WHERE (numero_factura IS NOT NULL);


--
-- Name: idx_solicitud_requisito_origen; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_requisito_origen ON public.solicitud_requisito USING btree (id_requisito_origen) WHERE (id_requisito_origen IS NOT NULL);


--
-- Name: idx_solicitud_requisito_solicitud; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_requisito_solicitud ON public.solicitud_requisito USING btree (id_solicitud);


--
-- Name: idx_solicitud_requisito_usuario_verificador; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_requisito_usuario_verificador ON public.solicitud_requisito USING btree (id_usuario_verificador) WHERE (id_usuario_verificador IS NOT NULL);


--
-- Name: idx_solicitud_solicitante; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_solicitante ON public.solicitud USING btree (id_solicitante);


--
-- Name: idx_solicitud_solicitante_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_solicitante_estado ON public.solicitud USING btree (id_solicitante, estado);


--
-- Name: idx_solicitud_tramite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_tramite ON public.solicitud USING btree (id_tramite);


--
-- Name: idx_token_recuperacion_expiracion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_recuperacion_expiracion ON public.token_recuperacion_contrasena USING btree (fecha_expiracion) WHERE ((fecha_utilizacion IS NULL) AND (fecha_revocacion IS NULL));


--
-- Name: idx_token_recuperacion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_recuperacion_usuario ON public.token_recuperacion_contrasena USING btree (id_usuario);


--
-- Name: idx_token_verificacion_correo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_verificacion_correo ON public.token_verificacion_correo USING btree (id_usuario_correo);


--
-- Name: idx_token_verificacion_expiracion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_verificacion_expiracion ON public.token_verificacion_correo USING btree (fecha_expiracion) WHERE ((fecha_utilizacion IS NULL) AND (fecha_revocacion IS NULL));


--
-- Name: idx_tramite_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_activo ON public.tramite USING btree (activo);


--
-- Name: idx_tramite_campo_orden; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_campo_orden ON public.tramite_campo USING btree (id_tramite, orden);


--
-- Name: idx_tramite_campo_tramite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_campo_tramite ON public.tramite_campo USING btree (id_tramite);


--
-- Name: idx_tramite_campo_tramite_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_campo_tramite_activo ON public.tramite_campo USING btree (id_tramite, activo);


--
-- Name: idx_tramite_catalogo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_catalogo ON public.tramite USING btree (activo, publicado);


--
-- Name: idx_tramite_publicado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_publicado ON public.tramite USING btree (publicado);


--
-- Name: idx_tramite_requisito_economico_codigo_externo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_requisito_economico_codigo_externo ON public.tramite_requisito_economico USING btree (codigo_concepto_externo) WHERE (codigo_concepto_externo IS NOT NULL);


--
-- Name: idx_tramite_requisito_economico_gestion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_requisito_economico_gestion ON public.tramite_requisito_economico USING btree (gestion, activo);


--
-- Name: idx_tramite_requisito_economico_requisito; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_requisito_economico_requisito ON public.tramite_requisito_economico USING btree (id_requisito);


--
-- Name: idx_tramite_requisito_orden; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_requisito_orden ON public.tramite_requisito USING btree (id_tramite, orden);


--
-- Name: idx_tramite_requisito_tramite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_requisito_tramite ON public.tramite_requisito USING btree (id_tramite);


--
-- Name: idx_tramite_requisito_tramite_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_requisito_tramite_activo ON public.tramite_requisito USING btree (id_tramite, activo);


--
-- Name: idx_unidad_administrativa_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_unidad_administrativa_activo ON public.unidad_administrativa USING btree (activo);


--
-- Name: idx_usuario_correo_busqueda; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_correo_busqueda ON public.usuario_correo USING btree (correo);


--
-- Name: idx_usuario_correo_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_correo_usuario ON public.usuario_correo USING btree (id_usuario);


--
-- Name: idx_usuario_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_estado ON public.usuario USING btree (estado);


--
-- Name: idx_usuario_rol_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_rol_activo ON public.usuario_rol USING btree (id_usuario, activo);


--
-- Name: idx_usuario_rol_rol; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_rol_rol ON public.usuario_rol USING btree (id_rol);


--
-- Name: idx_usuario_rol_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_rol_usuario ON public.usuario_rol USING btree (id_usuario);


--
-- Name: idx_usuario_unidad_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_unidad_activo ON public.usuario_unidad USING btree (id_unidad, activo);


--
-- Name: idx_usuario_unidad_unidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_unidad_unidad ON public.usuario_unidad USING btree (id_unidad);


--
-- Name: idx_usuario_unidad_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_unidad_usuario ON public.usuario_unidad USING btree (id_usuario);


--
-- Name: uq_chat_session_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_chat_session_usuario ON public.chat_session USING btree (id_usuario) WHERE (id_usuario IS NOT NULL);


--
-- Name: uq_intervencion_convocatoria_abierta; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_intervencion_convocatoria_abierta ON public.solicitud_intervencion USING btree (id_solicitud) WHERE ((estado)::text = 'convocada'::text);


--
-- Name: uq_notificacion_convocatoria; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_notificacion_convocatoria ON public.solicitud_notificacion USING btree (id_intervencion) WHERE ((tipo)::text = 'convocatoria'::text);


--
-- Name: uq_notificacion_observacion; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_notificacion_observacion ON public.solicitud_notificacion USING btree (id_observacion) WHERE ((tipo)::text = 'observacion'::text);


--
-- Name: uq_notificacion_resultado; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_notificacion_resultado ON public.solicitud_notificacion USING btree (id_solicitud) WHERE ((tipo)::text = 'resultado'::text);


--
-- Name: uq_pago_verificacion_factura_verificada; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pago_verificacion_factura_verificada ON public.solicitud_pago_verificacion USING btree (numero_factura_consultado) WHERE ((estado)::text = 'verificado'::text);


--
-- Name: uq_usuario_correo_principal_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_usuario_correo_principal_activo ON public.usuario_correo USING btree (id_usuario) WHERE ((es_principal = true) AND (activo = true));


--
-- Name: uq_usuario_correo_unico_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_usuario_correo_unico_activo ON public.usuario_correo USING btree (id_usuario) WHERE (activo = true);


--
-- Name: perfil_academico trg_perfil_academico_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_perfil_academico_fecha_actualizacion BEFORE UPDATE ON public.perfil_academico FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: rol trg_rol_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_rol_fecha_actualizacion BEFORE UPDATE ON public.rol FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: solicitud_dato trg_solicitud_dato_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_solicitud_dato_fecha_actualizacion BEFORE UPDATE ON public.solicitud_dato FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: solicitud trg_solicitud_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_solicitud_fecha_actualizacion BEFORE UPDATE ON public.solicitud FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: solicitud_requisito trg_solicitud_requisito_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_solicitud_requisito_fecha_actualizacion BEFORE UPDATE ON public.solicitud_requisito FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: tramite_campo trg_tramite_campo_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tramite_campo_fecha_actualizacion BEFORE UPDATE ON public.tramite_campo FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: tramite trg_tramite_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tramite_fecha_actualizacion BEFORE UPDATE ON public.tramite FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: tramite_requisito_economico trg_tramite_requisito_economico_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tramite_requisito_economico_fecha_actualizacion BEFORE UPDATE ON public.tramite_requisito_economico FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: tramite_requisito trg_tramite_requisito_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tramite_requisito_fecha_actualizacion BEFORE UPDATE ON public.tramite_requisito FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: unidad_administrativa trg_unidad_administrativa_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_unidad_administrativa_fecha_actualizacion BEFORE UPDATE ON public.unidad_administrativa FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: usuario_correo trg_usuario_correo_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_usuario_correo_fecha_actualizacion BEFORE UPDATE ON public.usuario_correo FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: usuario trg_usuario_fecha_actualizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_usuario_fecha_actualizacion BEFORE UPDATE ON public.usuario FOR EACH ROW EXECUTE FUNCTION public.actualizar_fecha_actualizacion();


--
-- Name: archivo_documento fk_archivo_documento_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archivo_documento
    ADD CONSTRAINT fk_archivo_documento_version FOREIGN KEY (id_version_documento) REFERENCES public.version_documento(id_version_documento) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: auditoria fk_auditoria_usuario_actor; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auditoria
    ADD CONSTRAINT fk_auditoria_usuario_actor FOREIGN KEY (id_usuario_actor) REFERENCES public.usuario(id_usuario) ON DELETE SET NULL;


--
-- Name: chat_message_feedback fk_chat_message_feedback_message; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_message_feedback
    ADD CONSTRAINT fk_chat_message_feedback_message FOREIGN KEY (message_id) REFERENCES public.chat_message(id_message) ON DELETE CASCADE;


--
-- Name: chat_message fk_chat_message_session; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_message
    ADD CONSTRAINT fk_chat_message_session FOREIGN KEY (session_id) REFERENCES public.chat_session(id_session) ON DELETE CASCADE;


--
-- Name: chat_session fk_chat_session_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_session
    ADD CONSTRAINT fk_chat_session_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: chunk_documento fk_chunk_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunk_documento
    ADD CONSTRAINT fk_chunk_version FOREIGN KEY (id_version_documento) REFERENCES public.version_documento(id_version_documento);


--
-- Name: documento_institucional fk_documento_version_actual; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_institucional
    ADD CONSTRAINT fk_documento_version_actual FOREIGN KEY (id_version_actual) REFERENCES public.version_documento(id_version_documento);


--
-- Name: evento_autenticacion fk_evento_autenticacion_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_autenticacion
    ADD CONSTRAINT fk_evento_autenticacion_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE SET NULL;


--
-- Name: solicitud_historial fk_historial_requisito; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_historial
    ADD CONSTRAINT fk_historial_requisito FOREIGN KEY (id_solicitud, id_solicitud_requisito) REFERENCES public.solicitud_requisito(id_solicitud, id_solicitud_requisito);


--
-- Name: solicitud_intervencion fk_intervencion_solicitud; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_intervencion
    ADD CONSTRAINT fk_intervencion_solicitud FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud) ON DELETE RESTRICT;


--
-- Name: solicitud_intervencion fk_intervencion_usuario_convocatoria; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_intervencion
    ADD CONSTRAINT fk_intervencion_usuario_convocatoria FOREIGN KEY (id_usuario_convocatoria) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: solicitud_intervencion fk_intervencion_usuario_registro; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_intervencion
    ADD CONSTRAINT fk_intervencion_usuario_registro FOREIGN KEY (id_usuario_registro) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: solicitud_notificacion fk_notificacion_intervencion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_notificacion
    ADD CONSTRAINT fk_notificacion_intervencion FOREIGN KEY (id_intervencion) REFERENCES public.solicitud_intervencion(id_intervencion) ON DELETE RESTRICT;


--
-- Name: solicitud_notificacion fk_notificacion_observacion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_notificacion
    ADD CONSTRAINT fk_notificacion_observacion FOREIGN KEY (id_observacion) REFERENCES public.solicitud_observacion(id_observacion) ON DELETE RESTRICT;


--
-- Name: solicitud_notificacion fk_notificacion_solicitud; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_notificacion
    ADD CONSTRAINT fk_notificacion_solicitud FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud) ON DELETE RESTRICT;


--
-- Name: solicitud_observacion fk_observacion_requisito; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_observacion
    ADD CONSTRAINT fk_observacion_requisito FOREIGN KEY (id_solicitud, id_solicitud_requisito) REFERENCES public.solicitud_requisito(id_solicitud, id_solicitud_requisito);


--
-- Name: solicitud_pago_verificacion fk_pago_verificacion_solicitud_requisito; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_pago_verificacion
    ADD CONSTRAINT fk_pago_verificacion_solicitud_requisito FOREIGN KEY (id_solicitud_requisito) REFERENCES public.solicitud_requisito(id_solicitud_requisito) ON DELETE RESTRICT;


--
-- Name: solicitud_pago_verificacion fk_pago_verificacion_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_pago_verificacion
    ADD CONSTRAINT fk_pago_verificacion_usuario FOREIGN KEY (id_usuario_verificador) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: perfil_academico fk_perfil_academico_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_academico
    ADD CONSTRAINT fk_perfil_academico_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: sesion_usuario fk_sesion_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT fk_sesion_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: solicitud_dato fk_solicitud_dato_campo; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_dato
    ADD CONSTRAINT fk_solicitud_dato_campo FOREIGN KEY (id_campo) REFERENCES public.tramite_campo(id_campo) ON DELETE RESTRICT;


--
-- Name: solicitud_dato fk_solicitud_dato_solicitud; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_dato
    ADD CONSTRAINT fk_solicitud_dato_solicitud FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud) ON DELETE CASCADE;


--
-- Name: solicitud_recepcion fk_solicitud_recepcion_solicitud; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_recepcion
    ADD CONSTRAINT fk_solicitud_recepcion_solicitud FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud) ON DELETE RESTRICT;


--
-- Name: solicitud_recepcion fk_solicitud_recepcion_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_recepcion
    ADD CONSTRAINT fk_solicitud_recepcion_usuario FOREIGN KEY (id_usuario_receptor) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: solicitud_requisito fk_solicitud_requisito_economico_origen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT fk_solicitud_requisito_economico_origen FOREIGN KEY (id_requisito_economico_origen) REFERENCES public.tramite_requisito_economico(id_requisito_economico) ON DELETE SET NULL;


--
-- Name: solicitud_requisito fk_solicitud_requisito_origen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT fk_solicitud_requisito_origen FOREIGN KEY (id_requisito_origen) REFERENCES public.tramite_requisito(id_requisito) ON DELETE SET NULL;


--
-- Name: solicitud_requisito fk_solicitud_requisito_solicitud; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT fk_solicitud_requisito_solicitud FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud) ON DELETE CASCADE;


--
-- Name: solicitud_requisito fk_solicitud_requisito_usuario_verificador; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT fk_solicitud_requisito_usuario_verificador FOREIGN KEY (id_usuario_verificador) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: solicitud fk_solicitud_solicitante; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud
    ADD CONSTRAINT fk_solicitud_solicitante FOREIGN KEY (id_solicitante) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: solicitud fk_solicitud_tramite; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud
    ADD CONSTRAINT fk_solicitud_tramite FOREIGN KEY (id_tramite) REFERENCES public.tramite(id_tramite) ON DELETE RESTRICT;


--
-- Name: token_recuperacion_contrasena fk_token_recuperacion_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_recuperacion_contrasena
    ADD CONSTRAINT fk_token_recuperacion_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: token_verificacion_correo fk_token_verificacion_correo; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_verificacion_correo
    ADD CONSTRAINT fk_token_verificacion_correo FOREIGN KEY (id_usuario_correo) REFERENCES public.usuario_correo(id_usuario_correo) ON DELETE CASCADE;


--
-- Name: tramite_campo fk_tramite_campo_tramite; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_campo
    ADD CONSTRAINT fk_tramite_campo_tramite FOREIGN KEY (id_tramite) REFERENCES public.tramite(id_tramite) ON DELETE CASCADE;


--
-- Name: tramite_requisito_economico fk_tramite_requisito_economico_requisito; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_requisito_economico
    ADD CONSTRAINT fk_tramite_requisito_economico_requisito FOREIGN KEY (id_requisito) REFERENCES public.tramite_requisito(id_requisito) ON DELETE CASCADE;


--
-- Name: tramite_requisito fk_tramite_requisito_tramite; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_requisito
    ADD CONSTRAINT fk_tramite_requisito_tramite FOREIGN KEY (id_tramite) REFERENCES public.tramite(id_tramite) ON DELETE CASCADE;


--
-- Name: usuario_correo fk_usuario_correo_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_correo
    ADD CONSTRAINT fk_usuario_correo_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: usuario_identidad_externa fk_usuario_identidad_externa_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_identidad_externa
    ADD CONSTRAINT fk_usuario_identidad_externa_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: usuario_rol fk_usuario_rol_asignado_por; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol
    ADD CONSTRAINT fk_usuario_rol_asignado_por FOREIGN KEY (asignado_por) REFERENCES public.usuario(id_usuario) ON DELETE SET NULL;


--
-- Name: usuario_rol fk_usuario_rol_rol; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol
    ADD CONSTRAINT fk_usuario_rol_rol FOREIGN KEY (id_rol) REFERENCES public.rol(id_rol);


--
-- Name: usuario_rol fk_usuario_rol_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol
    ADD CONSTRAINT fk_usuario_rol_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: usuario_unidad fk_usuario_unidad_asignado_por; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_unidad
    ADD CONSTRAINT fk_usuario_unidad_asignado_por FOREIGN KEY (asignado_por) REFERENCES public.usuario(id_usuario) ON DELETE SET NULL;


--
-- Name: usuario_unidad fk_usuario_unidad_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_unidad
    ADD CONSTRAINT fk_usuario_unidad_unidad FOREIGN KEY (id_unidad) REFERENCES public.unidad_administrativa(id_unidad) ON DELETE RESTRICT;


--
-- Name: usuario_unidad fk_usuario_unidad_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_unidad
    ADD CONSTRAINT fk_usuario_unidad_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE CASCADE;


--
-- Name: version_documento fk_version_documento; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.version_documento
    ADD CONSTRAINT fk_version_documento FOREIGN KEY (id_documento_institucional) REFERENCES public.documento_institucional(id_documento_institucional);


--
-- Name: solicitud_historial solicitud_historial_id_solicitud_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_historial
    ADD CONSTRAINT solicitud_historial_id_solicitud_fkey FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud) ON DELETE CASCADE;


--
-- Name: solicitud_historial solicitud_historial_id_usuario_actor_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_historial
    ADD CONSTRAINT solicitud_historial_id_usuario_actor_fkey FOREIGN KEY (id_usuario_actor) REFERENCES public.usuario(id_usuario) ON DELETE SET NULL;


--
-- Name: solicitud_observacion solicitud_observacion_id_solicitud_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_observacion
    ADD CONSTRAINT solicitud_observacion_id_solicitud_fkey FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud) ON DELETE RESTRICT;


--
-- Name: solicitud_observacion solicitud_observacion_id_usuario_observador_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_observacion
    ADD CONSTRAINT solicitud_observacion_id_usuario_observador_fkey FOREIGN KEY (id_usuario_observador) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: solicitud_observacion solicitud_observacion_id_usuario_resolucion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_observacion
    ADD CONSTRAINT solicitud_observacion_id_usuario_resolucion_fkey FOREIGN KEY (id_usuario_resolucion) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: solicitud_requisito solicitud_requisito_id_usuario_presentacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT solicitud_requisito_id_usuario_presentacion_fkey FOREIGN KEY (id_usuario_presentacion) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: solicitud_resultado solicitud_resultado_id_solicitud_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_resultado
    ADD CONSTRAINT solicitud_resultado_id_solicitud_fkey FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud) ON DELETE RESTRICT;


--
-- Name: solicitud_resultado solicitud_resultado_id_usuario_registro_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_resultado
    ADD CONSTRAINT solicitud_resultado_id_usuario_registro_fkey FOREIGN KEY (id_usuario_registro) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict YJYAnUi3QNuUagj1hckIeCT74N5kMw7M6KWrw4LnzxJ8PhxXWNEkF8W1wiBSLNm

