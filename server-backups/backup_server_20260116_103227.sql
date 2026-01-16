--
-- PostgreSQL database dump
--

\restrict 6WqsbBS0D3gP1bf3LLp3tFab9Rc35WrSr8OR6FGPHmmTkWZrklrlBmrnhOLe3Ke

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: tenant_1; Type: SCHEMA; Schema: -; Owner: barber_user
--

CREATE SCHEMA tenant_1;


ALTER SCHEMA tenant_1 OWNER TO barber_user;

--
-- Name: tenant_8; Type: SCHEMA; Schema: -; Owner: barber_user
--

CREATE SCHEMA tenant_8;


ALTER SCHEMA tenant_8 OWNER TO barber_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(250) NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.alembic_version OWNER TO barber_user;

--
-- Name: blocked_slots; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.blocked_slots (
    id integer NOT NULL,
    block_type character varying(50) NOT NULL,
    master_id integer,
    post_id integer,
    service_id integer,
    start_date date NOT NULL,
    end_date date NOT NULL,
    start_time time without time zone,
    end_time time without time zone,
    reason text,
    created_by integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.blocked_slots OWNER TO barber_user;

--
-- Name: blocked_slots_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.blocked_slots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.blocked_slots_id_seq OWNER TO barber_user;

--
-- Name: blocked_slots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.blocked_slots_id_seq OWNED BY public.blocked_slots.id;


--
-- Name: booking_history; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.booking_history (
    id integer NOT NULL,
    booking_id integer NOT NULL,
    changed_by integer,
    field_name character varying(100) NOT NULL,
    old_value text,
    new_value text,
    changed_at timestamp without time zone NOT NULL
);


ALTER TABLE public.booking_history OWNER TO barber_user;

--
-- Name: booking_history_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.booking_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.booking_history_id_seq OWNER TO barber_user;

--
-- Name: booking_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.booking_history_id_seq OWNED BY public.booking_history.id;


--
-- Name: bookings; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.bookings (
    id integer NOT NULL,
    booking_number character varying(50) NOT NULL,
    client_id integer NOT NULL,
    service_id integer,
    master_id integer,
    post_id integer,
    created_by integer,
    date date NOT NULL,
    "time" time without time zone NOT NULL,
    duration integer NOT NULL,
    end_time time without time zone NOT NULL,
    status character varying(50) NOT NULL,
    amount numeric(10,2),
    is_paid boolean NOT NULL,
    payment_method character varying(50),
    promocode_id integer,
    discount_amount numeric(10,2) NOT NULL,
    comment text,
    admin_comment text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    confirmed_at timestamp without time zone,
    completed_at timestamp without time zone,
    cancelled_at timestamp without time zone
);


ALTER TABLE public.bookings OWNER TO barber_user;

--
-- Name: bookings_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.bookings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.bookings_id_seq OWNER TO barber_user;

--
-- Name: bookings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.bookings_id_seq OWNED BY public.bookings.id;


--
-- Name: broadcasts; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.broadcasts (
    id integer NOT NULL,
    text text NOT NULL,
    image_path character varying(500),
    target_audience character varying(50) NOT NULL,
    filter_params jsonb,
    status character varying(50) NOT NULL,
    total_sent integer NOT NULL,
    total_errors integer NOT NULL,
    created_by integer,
    created_at timestamp without time zone NOT NULL,
    sent_at timestamp without time zone
);


ALTER TABLE public.broadcasts OWNER TO barber_user;

--
-- Name: broadcasts_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.broadcasts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.broadcasts_id_seq OWNER TO barber_user;

--
-- Name: broadcasts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.broadcasts_id_seq OWNED BY public.broadcasts.id;


--
-- Name: client_history; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.client_history (
    id integer NOT NULL,
    client_id integer NOT NULL,
    booking_id integer NOT NULL,
    service_id integer,
    master_id integer,
    date date NOT NULL,
    amount numeric(10,2),
    notes text,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.client_history OWNER TO barber_user;

--
-- Name: client_history_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.client_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.client_history_id_seq OWNER TO barber_user;

--
-- Name: client_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.client_history_id_seq OWNED BY public.client_history.id;


--
-- Name: clients; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.clients (
    id integer NOT NULL,
    user_id integer NOT NULL,
    full_name character varying(255) NOT NULL,
    phone character varying(20) NOT NULL,
    total_visits integer NOT NULL,
    total_amount numeric(10,2) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.clients OWNER TO barber_user;

--
-- Name: clients_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.clients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.clients_id_seq OWNER TO barber_user;

--
-- Name: clients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.clients_id_seq OWNED BY public.clients.id;


--
-- Name: companies; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.companies (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    email character varying(255),
    phone character varying(20),
    telegram_bot_token character varying(500),
    telegram_bot_username character varying(100),
    admin_telegram_id bigint,
    telegram_admin_ids bigint[],
    plan_id integer,
    subscription_status character varying(50) DEFAULT 'pending'::character varying,
    subscription_end_date date,
    can_create_bookings boolean DEFAULT true,
    password_hash character varying(255),
    password_changed_at timestamp without time zone,
    password_reset_token character varying(255),
    password_reset_expires_at timestamp without time zone,
    webhook_url character varying(500),
    api_key character varying(255),
    is_active boolean DEFAULT true,
    is_blocked boolean DEFAULT false,
    blocked_reason text,
    blocked_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.companies OWNER TO barber_user;

--
-- Name: companies_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.companies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.companies_id_seq OWNER TO barber_user;

--
-- Name: companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.companies_id_seq OWNED BY public.companies.id;


--
-- Name: master_services; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.master_services (
    id integer NOT NULL,
    master_id integer NOT NULL,
    service_id integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.master_services OWNER TO barber_user;

--
-- Name: master_services_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.master_services_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.master_services_id_seq OWNER TO barber_user;

--
-- Name: master_services_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.master_services_id_seq OWNED BY public.master_services.id;


--
-- Name: masters; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.masters (
    id integer NOT NULL,
    user_id integer,
    full_name character varying(255) NOT NULL,
    phone character varying(20),
    telegram_id bigint,
    specialization character varying(100),
    is_universal boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.masters OWNER TO barber_user;

--
-- Name: masters_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.masters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.masters_id_seq OWNER TO barber_user;

--
-- Name: masters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.masters_id_seq OWNED BY public.masters.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    booking_id integer,
    notification_type character varying(50) NOT NULL,
    message text NOT NULL,
    is_sent boolean NOT NULL,
    sent_at timestamp without time zone,
    error_message text,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.notifications OWNER TO barber_user;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.notifications_id_seq OWNER TO barber_user;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    company_id integer,
    plan_id integer NOT NULL,
    subscription_id integer,
    amount numeric(10,2) NOT NULL,
    currency character varying(3) NOT NULL,
    status character varying(20),
    yookassa_payment_id character varying(100) NOT NULL,
    yookassa_payment_status character varying(50),
    yookassa_confirmation_url character varying(500),
    yookassa_return_url character varying(500),
    webhook_payload jsonb,
    webhook_received_at timestamp with time zone,
    webhook_signature_verified boolean,
    description character varying(500),
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.payments OWNER TO barber_user;

--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.payments_id_seq OWNER TO barber_user;

--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: plans; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.plans (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(500),
    price_monthly numeric(10,2) NOT NULL,
    price_yearly numeric(10,2) NOT NULL,
    max_bookings_per_month integer,
    max_users integer,
    max_masters integer,
    max_posts integer,
    max_promotions integer,
    display_order integer,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.plans OWNER TO barber_user;

--
-- Name: plans_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.plans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.plans_id_seq OWNER TO barber_user;

--
-- Name: plans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.plans_id_seq OWNED BY public.plans.id;


--
-- Name: posts; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.posts (
    id integer NOT NULL,
    number integer NOT NULL,
    name character varying(255),
    description text,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.posts OWNER TO barber_user;

--
-- Name: posts_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.posts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.posts_id_seq OWNER TO barber_user;

--
-- Name: posts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.posts_id_seq OWNED BY public.posts.id;


--
-- Name: promocodes; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.promocodes (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    discount_type character varying(20) NOT NULL,
    discount_value numeric(10,2) NOT NULL,
    service_id integer,
    min_amount numeric(10,2) NOT NULL,
    max_uses integer,
    current_uses integer NOT NULL,
    start_date date,
    end_date date,
    is_active boolean NOT NULL,
    description text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.promocodes OWNER TO barber_user;

--
-- Name: promocodes_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.promocodes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.promocodes_id_seq OWNER TO barber_user;

--
-- Name: promocodes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.promocodes_id_seq OWNED BY public.promocodes.id;


--
-- Name: promotions; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.promotions (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    discount_type character varying(20) NOT NULL,
    discount_value numeric(10,2) NOT NULL,
    service_id integer,
    start_date date,
    end_date date,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.promotions OWNER TO barber_user;

--
-- Name: promotions_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.promotions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.promotions_id_seq OWNER TO barber_user;

--
-- Name: promotions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.promotions_id_seq OWNED BY public.promotions.id;


--
-- Name: services; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.services (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    duration integer NOT NULL,
    price numeric(10,2) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.services OWNER TO barber_user;

--
-- Name: services_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.services_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.services_id_seq OWNER TO barber_user;

--
-- Name: services_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.services_id_seq OWNED BY public.services.id;


--
-- Name: settings; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.settings (
    id integer NOT NULL,
    key character varying(100) NOT NULL,
    value text,
    description text,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.settings OWNER TO barber_user;

--
-- Name: settings_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.settings_id_seq OWNER TO barber_user;

--
-- Name: settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.settings_id_seq OWNED BY public.settings.id;


--
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.subscriptions (
    id integer NOT NULL,
    company_id integer NOT NULL,
    plan_id integer NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    cancelled_at timestamp with time zone,
    status character varying(20),
    trial_used boolean,
    auto_renewal boolean,
    extra_data jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.subscriptions OWNER TO barber_user;

--
-- Name: subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.subscriptions_id_seq OWNER TO barber_user;

--
-- Name: subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.subscriptions_id_seq OWNED BY public.subscriptions.id;


--
-- Name: super_admins; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.super_admins (
    id integer NOT NULL,
    username character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    telegram_id integer,
    phone character varying(20),
    is_super_admin boolean,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.super_admins OWNER TO barber_user;

--
-- Name: super_admins_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.super_admins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.super_admins_id_seq OWNER TO barber_user;

--
-- Name: super_admins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.super_admins_id_seq OWNED BY public.super_admins.id;


--
-- Name: timeslots; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.timeslots (
    id integer NOT NULL,
    date date NOT NULL,
    "time" time without time zone NOT NULL,
    is_available boolean NOT NULL,
    booking_id integer,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.timeslots OWNER TO barber_user;

--
-- Name: timeslots_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.timeslots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.timeslots_id_seq OWNER TO barber_user;

--
-- Name: timeslots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.timeslots_id_seq OWNED BY public.timeslots.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: barber_user
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(255),
    first_name character varying(255),
    last_name character varying(255),
    phone character varying(20),
    is_admin boolean NOT NULL,
    is_master boolean NOT NULL,
    is_blocked boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.users OWNER TO barber_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: barber_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO barber_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: barber_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: blocked_slots; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.blocked_slots (
    id integer,
    block_type character varying(50),
    master_id integer,
    post_id integer,
    service_id integer,
    start_date date,
    end_date date,
    start_time time without time zone,
    end_time time without time zone,
    reason text,
    created_by integer,
    created_at timestamp without time zone
);


ALTER TABLE tenant_1.blocked_slots OWNER TO barber_user;

--
-- Name: booking_history; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.booking_history (
    id integer,
    booking_id integer,
    changed_by integer,
    field_name character varying(100),
    old_value text,
    new_value text,
    changed_at timestamp without time zone
);


ALTER TABLE tenant_1.booking_history OWNER TO barber_user;

--
-- Name: bookings; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.bookings (
    id integer,
    booking_number character varying(50),
    client_id integer,
    service_id integer,
    master_id integer,
    post_id integer,
    created_by integer,
    date date,
    "time" time without time zone,
    duration integer,
    end_time time without time zone,
    status character varying(50),
    amount numeric(10,2),
    is_paid boolean,
    payment_method character varying(50),
    promocode_id integer,
    discount_amount numeric(10,2),
    comment text,
    admin_comment text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    confirmed_at timestamp without time zone,
    completed_at timestamp without time zone,
    cancelled_at timestamp without time zone
);


ALTER TABLE tenant_1.bookings OWNER TO barber_user;

--
-- Name: broadcasts; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.broadcasts (
    id integer,
    text text,
    image_path character varying(500),
    target_audience character varying(50),
    filter_params jsonb,
    status character varying(50),
    total_sent integer,
    total_errors integer,
    created_by integer,
    created_at timestamp without time zone,
    sent_at timestamp without time zone
);


ALTER TABLE tenant_1.broadcasts OWNER TO barber_user;

--
-- Name: client_history; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.client_history (
    id integer,
    client_id integer,
    booking_id integer,
    service_id integer,
    master_id integer,
    date date,
    amount numeric(10,2),
    notes text,
    created_at timestamp without time zone
);


ALTER TABLE tenant_1.client_history OWNER TO barber_user;

--
-- Name: clients; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.clients (
    id integer,
    user_id integer,
    full_name character varying(255),
    phone character varying(20),
    total_visits integer,
    total_amount numeric(10,2),
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE tenant_1.clients OWNER TO barber_user;

--
-- Name: master_services; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.master_services (
    id integer,
    master_id integer,
    service_id integer,
    created_at timestamp without time zone
);


ALTER TABLE tenant_1.master_services OWNER TO barber_user;

--
-- Name: masters; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.masters (
    id integer,
    user_id integer,
    full_name character varying(255),
    phone character varying(20),
    telegram_id bigint,
    specialization character varying(100),
    is_universal boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE tenant_1.masters OWNER TO barber_user;

--
-- Name: notifications; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.notifications (
    id integer,
    user_id integer,
    booking_id integer,
    notification_type character varying(50),
    message text,
    is_sent boolean,
    sent_at timestamp without time zone,
    error_message text,
    created_at timestamp without time zone
);


ALTER TABLE tenant_1.notifications OWNER TO barber_user;

--
-- Name: posts; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.posts (
    id integer,
    number integer,
    name character varying(255),
    description text,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE tenant_1.posts OWNER TO barber_user;

--
-- Name: promocodes; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.promocodes (
    id integer,
    code character varying(50),
    discount_type character varying(20),
    discount_value numeric(10,2),
    service_id integer,
    min_amount numeric(10,2),
    max_uses integer,
    current_uses integer,
    start_date date,
    end_date date,
    is_active boolean,
    description text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE tenant_1.promocodes OWNER TO barber_user;

--
-- Name: promotions; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.promotions (
    id integer,
    name character varying(255),
    description text,
    discount_type character varying(20),
    discount_value numeric(10,2),
    service_id integer,
    start_date date,
    end_date date,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE tenant_1.promotions OWNER TO barber_user;

--
-- Name: services; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.services (
    id integer,
    name character varying(255),
    description text,
    duration integer,
    price numeric(10,2),
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE tenant_1.services OWNER TO barber_user;

--
-- Name: settings; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.settings (
    id integer,
    key character varying(100),
    value text,
    description text,
    updated_at timestamp without time zone
);


ALTER TABLE tenant_1.settings OWNER TO barber_user;

--
-- Name: timeslots; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.timeslots (
    id integer,
    date date,
    "time" time without time zone,
    is_available boolean,
    booking_id integer,
    created_at timestamp without time zone
);


ALTER TABLE tenant_1.timeslots OWNER TO barber_user;

--
-- Name: users; Type: TABLE; Schema: tenant_1; Owner: barber_user
--

CREATE TABLE tenant_1.users (
    id integer,
    telegram_id bigint,
    username character varying(255),
    first_name character varying(255),
    last_name character varying(255),
    phone character varying(20),
    is_admin boolean,
    is_master boolean,
    is_blocked boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    email character varying(255),
    role character varying(20) DEFAULT 'client'::character varying,
    full_name character varying(255)
);


ALTER TABLE tenant_1.users OWNER TO barber_user;

--
-- Name: bookings; Type: TABLE; Schema: tenant_8; Owner: barber_user
--

CREATE TABLE tenant_8.bookings (
    id integer NOT NULL,
    booking_number character varying(50) NOT NULL,
    client_id integer NOT NULL,
    service_id integer,
    master_id integer,
    post_id integer,
    created_by integer,
    date date NOT NULL,
    "time" time without time zone NOT NULL,
    duration integer NOT NULL,
    end_time time without time zone NOT NULL,
    status character varying(50) DEFAULT 'new'::character varying NOT NULL,
    amount numeric(10,2),
    is_paid boolean DEFAULT false NOT NULL,
    payment_method character varying(50),
    promocode_id integer,
    discount_amount numeric(10,2) DEFAULT 0.00 NOT NULL,
    comment text,
    admin_comment text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    confirmed_at timestamp without time zone,
    completed_at timestamp without time zone,
    cancelled_at timestamp without time zone
);


ALTER TABLE tenant_8.bookings OWNER TO barber_user;

--
-- Name: bookings_id_seq; Type: SEQUENCE; Schema: tenant_8; Owner: barber_user
--

CREATE SEQUENCE tenant_8.bookings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE tenant_8.bookings_id_seq OWNER TO barber_user;

--
-- Name: bookings_id_seq; Type: SEQUENCE OWNED BY; Schema: tenant_8; Owner: barber_user
--

ALTER SEQUENCE tenant_8.bookings_id_seq OWNED BY tenant_8.bookings.id;


--
-- Name: clients; Type: TABLE; Schema: tenant_8; Owner: barber_user
--

CREATE TABLE tenant_8.clients (
    id integer NOT NULL,
    user_id integer,
    full_name character varying(255) NOT NULL,
    phone character varying(20),
    email character varying(255),
    telegram_id bigint,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE tenant_8.clients OWNER TO barber_user;

--
-- Name: clients_id_seq; Type: SEQUENCE; Schema: tenant_8; Owner: barber_user
--

CREATE SEQUENCE tenant_8.clients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE tenant_8.clients_id_seq OWNER TO barber_user;

--
-- Name: clients_id_seq; Type: SEQUENCE OWNED BY; Schema: tenant_8; Owner: barber_user
--

ALTER SEQUENCE tenant_8.clients_id_seq OWNED BY tenant_8.clients.id;


--
-- Name: masters; Type: TABLE; Schema: tenant_8; Owner: barber_user
--

CREATE TABLE tenant_8.masters (
    id integer NOT NULL,
    user_id integer,
    full_name character varying(255) NOT NULL,
    phone character varying(20),
    telegram_id bigint,
    specialization character varying(100),
    is_universal boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE tenant_8.masters OWNER TO barber_user;

--
-- Name: masters_id_seq; Type: SEQUENCE; Schema: tenant_8; Owner: barber_user
--

CREATE SEQUENCE tenant_8.masters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE tenant_8.masters_id_seq OWNER TO barber_user;

--
-- Name: masters_id_seq; Type: SEQUENCE OWNED BY; Schema: tenant_8; Owner: barber_user
--

ALTER SEQUENCE tenant_8.masters_id_seq OWNED BY tenant_8.masters.id;


--
-- Name: posts; Type: TABLE; Schema: tenant_8; Owner: barber_user
--

CREATE TABLE tenant_8.posts (
    id integer NOT NULL,
    number integer NOT NULL,
    name character varying(255),
    description text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE tenant_8.posts OWNER TO barber_user;

--
-- Name: posts_id_seq; Type: SEQUENCE; Schema: tenant_8; Owner: barber_user
--

CREATE SEQUENCE tenant_8.posts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE tenant_8.posts_id_seq OWNER TO barber_user;

--
-- Name: posts_id_seq; Type: SEQUENCE OWNED BY; Schema: tenant_8; Owner: barber_user
--

ALTER SEQUENCE tenant_8.posts_id_seq OWNED BY tenant_8.posts.id;


--
-- Name: services; Type: TABLE; Schema: tenant_8; Owner: barber_user
--

CREATE TABLE tenant_8.services (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    duration integer NOT NULL,
    price numeric(10,2) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE tenant_8.services OWNER TO barber_user;

--
-- Name: services_id_seq; Type: SEQUENCE; Schema: tenant_8; Owner: barber_user
--

CREATE SEQUENCE tenant_8.services_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE tenant_8.services_id_seq OWNER TO barber_user;

--
-- Name: services_id_seq; Type: SEQUENCE OWNED BY; Schema: tenant_8; Owner: barber_user
--

ALTER SEQUENCE tenant_8.services_id_seq OWNED BY tenant_8.services.id;


--
-- Name: users; Type: TABLE; Schema: tenant_8; Owner: barber_user
--

CREATE TABLE tenant_8.users (
    id integer NOT NULL,
    username character varying(100) NOT NULL,
    email character varying(255),
    password_hash character varying(255) NOT NULL,
    full_name character varying(255),
    phone character varying(20),
    role character varying(50) DEFAULT 'client'::character varying,
    telegram_id bigint,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE tenant_8.users OWNER TO barber_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: tenant_8; Owner: barber_user
--

CREATE SEQUENCE tenant_8.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE tenant_8.users_id_seq OWNER TO barber_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: tenant_8; Owner: barber_user
--

ALTER SEQUENCE tenant_8.users_id_seq OWNED BY tenant_8.users.id;


--
-- Name: blocked_slots id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.blocked_slots ALTER COLUMN id SET DEFAULT nextval('public.blocked_slots_id_seq'::regclass);


--
-- Name: booking_history id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.booking_history ALTER COLUMN id SET DEFAULT nextval('public.booking_history_id_seq'::regclass);


--
-- Name: bookings id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.bookings ALTER COLUMN id SET DEFAULT nextval('public.bookings_id_seq'::regclass);


--
-- Name: broadcasts id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.broadcasts ALTER COLUMN id SET DEFAULT nextval('public.broadcasts_id_seq'::regclass);


--
-- Name: client_history id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.client_history ALTER COLUMN id SET DEFAULT nextval('public.client_history_id_seq'::regclass);


--
-- Name: clients id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.clients ALTER COLUMN id SET DEFAULT nextval('public.clients_id_seq'::regclass);


--
-- Name: companies id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.companies ALTER COLUMN id SET DEFAULT nextval('public.companies_id_seq'::regclass);


--
-- Name: master_services id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.master_services ALTER COLUMN id SET DEFAULT nextval('public.master_services_id_seq'::regclass);


--
-- Name: masters id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.masters ALTER COLUMN id SET DEFAULT nextval('public.masters_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: plans id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.plans ALTER COLUMN id SET DEFAULT nextval('public.plans_id_seq'::regclass);


--
-- Name: posts id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.posts ALTER COLUMN id SET DEFAULT nextval('public.posts_id_seq'::regclass);


--
-- Name: promocodes id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.promocodes ALTER COLUMN id SET DEFAULT nextval('public.promocodes_id_seq'::regclass);


--
-- Name: promotions id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.promotions ALTER COLUMN id SET DEFAULT nextval('public.promotions_id_seq'::regclass);


--
-- Name: services id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.services ALTER COLUMN id SET DEFAULT nextval('public.services_id_seq'::regclass);


--
-- Name: settings id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.settings ALTER COLUMN id SET DEFAULT nextval('public.settings_id_seq'::regclass);


--
-- Name: subscriptions id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.subscriptions ALTER COLUMN id SET DEFAULT nextval('public.subscriptions_id_seq'::regclass);


--
-- Name: super_admins id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.super_admins ALTER COLUMN id SET DEFAULT nextval('public.super_admins_id_seq'::regclass);


--
-- Name: timeslots id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.timeslots ALTER COLUMN id SET DEFAULT nextval('public.timeslots_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: bookings id; Type: DEFAULT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.bookings ALTER COLUMN id SET DEFAULT nextval('tenant_8.bookings_id_seq'::regclass);


--
-- Name: clients id; Type: DEFAULT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.clients ALTER COLUMN id SET DEFAULT nextval('tenant_8.clients_id_seq'::regclass);


--
-- Name: masters id; Type: DEFAULT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.masters ALTER COLUMN id SET DEFAULT nextval('tenant_8.masters_id_seq'::regclass);


--
-- Name: posts id; Type: DEFAULT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.posts ALTER COLUMN id SET DEFAULT nextval('tenant_8.posts_id_seq'::regclass);


--
-- Name: services id; Type: DEFAULT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.services ALTER COLUMN id SET DEFAULT nextval('tenant_8.services_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.users ALTER COLUMN id SET DEFAULT nextval('tenant_8.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.alembic_version (version_num, created_at) FROM stdin;
\.


--
-- Data for Name: blocked_slots; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.blocked_slots (id, block_type, master_id, post_id, service_id, start_date, end_date, start_time, end_time, reason, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: booking_history; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.booking_history (id, booking_id, changed_by, field_name, old_value, new_value, changed_at) FROM stdin;
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.bookings (id, booking_number, client_id, service_id, master_id, post_id, created_by, date, "time", duration, end_time, status, amount, is_paid, payment_method, promocode_id, discount_amount, comment, admin_comment, created_at, updated_at, confirmed_at, completed_at, cancelled_at) FROM stdin;
\.


--
-- Data for Name: broadcasts; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.broadcasts (id, text, image_path, target_audience, filter_params, status, total_sent, total_errors, created_by, created_at, sent_at) FROM stdin;
\.


--
-- Data for Name: client_history; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.client_history (id, client_id, booking_id, service_id, master_id, date, amount, notes, created_at) FROM stdin;
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.clients (id, user_id, full_name, phone, total_visits, total_amount, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.companies (id, name, email, phone, telegram_bot_token, telegram_bot_username, admin_telegram_id, telegram_admin_ids, plan_id, subscription_status, subscription_end_date, can_create_bookings, password_hash, password_changed_at, password_reset_token, password_reset_expires_at, webhook_url, api_key, is_active, is_blocked, blocked_reason, blocked_at, created_at, updated_at) FROM stdin;
8	Автосервис	+79610211760	+79610211760	8214331847:AAEV8pWvwvTNtlrRDBoNtu_w6ZLPmJMC25o	barber77_1_bot	329621295	\N	1	active	\N	t	\N	\N	\N	\N	\N	\N	t	f	\N	\N	2026-01-14 04:09:50.761171	2026-01-14 08:38:38.861319
\.


--
-- Data for Name: master_services; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.master_services (id, master_id, service_id, created_at) FROM stdin;
\.


--
-- Data for Name: masters; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.masters (id, user_id, full_name, phone, telegram_id, specialization, is_universal, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.notifications (id, user_id, booking_id, notification_type, message, is_sent, sent_at, error_message, created_at) FROM stdin;
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.payments (id, company_id, plan_id, subscription_id, amount, currency, status, yookassa_payment_id, yookassa_payment_status, yookassa_confirmation_url, yookassa_return_url, webhook_payload, webhook_received_at, webhook_signature_verified, description, extra_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: plans; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.plans (id, name, description, price_monthly, price_yearly, max_bookings_per_month, max_users, max_masters, max_posts, max_promotions, display_order, is_active, created_at, updated_at) FROM stdin;
1	Starter	Базовый план для начала работы	0.00	0.00	50	1	1	1	0	1	t	2026-01-16 00:44:50.622744+03	\N
2	Standard	Стандартный план для растущего бизнеса	2990.00	29900.00	500	5	5	5	10	2	t	2026-01-16 00:44:50.622744+03	\N
3	Business	Расширенный план для крупных компаний	6990.00	69900.00	2000	20	20	10	50	3	t	2026-01-16 00:44:50.622744+03	\N
4	Enterprise	Корпоративный план с дополнительными возможностями	14990.00	149900.00	5000	100	50	20	100	4	t	2026-01-16 00:44:50.622744+03	\N
\.


--
-- Data for Name: posts; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.posts (id, number, name, description, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: promocodes; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.promocodes (id, code, discount_type, discount_value, service_id, min_amount, max_uses, current_uses, start_date, end_date, is_active, description, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: promotions; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.promotions (id, name, description, discount_type, discount_value, service_id, start_date, end_date, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: services; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.services (id, name, description, duration, price, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: settings; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.settings (id, key, value, description, updated_at) FROM stdin;
\.


--
-- Data for Name: subscriptions; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.subscriptions (id, company_id, plan_id, start_date, end_date, cancelled_at, status, trial_used, auto_renewal, extra_data, created_at, updated_at) FROM stdin;
8	8	1	2026-01-14	2026-02-13	\N	active	f	f	\N	2026-01-14 07:09:50.76269+03	\N
\.


--
-- Data for Name: super_admins; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.super_admins (id, username, email, password_hash, telegram_id, phone, is_super_admin, is_active, created_at, updated_at) FROM stdin;
1	admin	admin@autoservice.com	$2b$12$Febbmnqa0Xyk.9T1eSdtbe49wG2bRSaJzDzViO8/dTFy/8V5/wara	\N	\N	t	t	2026-01-16 00:59:01.167461+03	\N
\.


--
-- Data for Name: timeslots; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.timeslots (id, date, "time", is_available, booking_id, created_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: barber_user
--

COPY public.users (id, telegram_id, username, first_name, last_name, phone, is_admin, is_master, is_blocked, created_at, updated_at) FROM stdin;
1	329621295	komarofleo	Leonid	Komarov	\N	t	f	f	2026-01-14 08:56:56.825119	2026-01-14 08:56:56.825123
\.


--
-- Data for Name: blocked_slots; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.blocked_slots (id, block_type, master_id, post_id, service_id, start_date, end_date, start_time, end_time, reason, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: booking_history; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.booking_history (id, booking_id, changed_by, field_name, old_value, new_value, changed_at) FROM stdin;
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.bookings (id, booking_number, client_id, service_id, master_id, post_id, created_by, date, "time", duration, end_time, status, amount, is_paid, payment_method, promocode_id, discount_amount, comment, admin_comment, created_at, updated_at, confirmed_at, completed_at, cancelled_at) FROM stdin;
1	BK00820260101001	1	1	1	1	\N	2026-01-01	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
2	BK00820260101002	1	1	1	1	\N	2026-01-01	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
3	BK00820260101003	1	1	1	1	\N	2026-01-01	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
4	BK00820260102001	1	1	1	1	\N	2026-01-02	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
5	BK00820260102002	1	1	1	1	\N	2026-01-02	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
6	BK00820260102003	1	1	1	1	\N	2026-01-02	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
7	BK00820260103001	1	1	1	1	\N	2026-01-03	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
8	BK00820260103002	1	1	1	1	\N	2026-01-03	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
9	BK00820260103003	1	1	1	1	\N	2026-01-03	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
10	BK00820260105001	1	1	1	1	\N	2026-01-05	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
11	BK00820260105002	1	1	1	1	\N	2026-01-05	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
12	BK00820260105003	1	1	1	1	\N	2026-01-05	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
13	BK00820260106001	1	1	1	1	\N	2026-01-06	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
14	BK00820260106002	1	1	1	1	\N	2026-01-06	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
15	BK00820260106003	1	1	1	1	\N	2026-01-06	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
16	BK00820260107001	1	1	1	1	\N	2026-01-07	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
17	BK00820260107002	1	1	1	1	\N	2026-01-07	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
18	BK00820260107003	1	1	1	1	\N	2026-01-07	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
19	BK00820260108001	1	1	1	1	\N	2026-01-08	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
20	BK00820260108002	1	1	1	1	\N	2026-01-08	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
21	BK00820260108003	1	1	1	1	\N	2026-01-08	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
22	BK00820260109001	1	1	1	1	\N	2026-01-09	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
23	BK00820260109002	1	1	1	1	\N	2026-01-09	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
24	BK00820260109003	1	1	1	1	\N	2026-01-09	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
25	BK00820260110001	1	1	1	1	\N	2026-01-10	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
26	BK00820260110002	1	1	1	1	\N	2026-01-10	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
27	BK00820260110003	1	1	1	1	\N	2026-01-10	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
28	BK00820260112001	1	1	1	1	\N	2026-01-12	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
29	BK00820260112002	1	1	1	1	\N	2026-01-12	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
30	BK00820260112003	1	1	1	1	\N	2026-01-12	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
35	B-20260115-005	6	5	\N	\N	11	2026-01-15	14:30:00	150	17:00:00	cancelled	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:18:13.457871	2026-01-14 14:55:13.764516	\N	\N	\N
40	B-20260116-001	8	2	4	2	13	2026-01-16	13:30:00	60	14:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 04:55:57.604577	2026-01-15 06:09:24.0553	2026-01-15 06:08:01.614023	\N	\N
34	B-20260115-004	6	5	\N	\N	11	2026-01-15	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:17:49.693194	2026-01-14 14:53:00.830902	\N	\N	\N
36	B-20260115-006	6	5	\N	\N	11	2026-01-15	15:30:00	150	18:00:00	completed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:18:15.860349	2026-01-14 15:31:09.380582	\N	2026-01-14 15:31:09.370942	\N
39	B-20260123-001	7	1	3	1	12	2026-01-23	15:30:00	30	16:00:00	completed	1200.00	t	cash	\N	0.00	\N	\N	2026-01-14 15:09:45.425435	2026-01-15 06:10:21.73395	2026-01-15 06:08:43.981685	2026-01-15 06:09:53.038509	\N
44	BK00820260115063757	7	5	2	4	1	2026-01-16	10:30:00	150	13:00:00	confirmed	\N	f	\N	\N	0.00	ок	\N	2026-01-15 06:37:57.991996	2026-01-15 08:42:19.602735	2026-01-15 08:42:19.602735	\N	\N
33	B-20260115-003	6	5	\N	2	11	2026-01-15	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:17:48.401578	2026-01-15 16:22:09.120645	2026-01-15 16:22:09.120645	\N	\N
47	BK00820260115065326	7	1	2	4	1	2026-01-16	10:00:00	30	10:30:00	cancelled	\N	f	\N	\N	0.00	\N	\N	2026-01-15 06:53:26.969857	2026-01-15 16:48:19.23251	2026-01-15 10:59:26.754951	\N	2026-01-15 16:48:19.144742
49	BK00820260115071652	7	5	4	3	1	2026-01-16	15:00:00	150	17:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 07:16:52.282592	2026-01-15 10:58:54.835527	2026-01-15 10:58:54.835527	\N	\N
42	B-20260131-001	7	1	4	2	12	2026-01-31	17:00:00	30	17:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 06:11:49.918406	2026-01-15 10:31:35.465331	2026-01-15 10:31:26.850495	\N	\N
50	BK00820260115072132	7	4	4	\N	1	2026-01-16	13:00:00	45	13:45:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 07:21:32.850318	2026-01-15 14:12:22.785588	2026-01-15 14:12:22.785588	\N	\N
52	BK00820260115072913	7	4	4	2	1	2026-01-17	14:00:00	45	14:45:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 07:29:13.257947	2026-01-15 14:12:31.657704	2026-01-15 14:12:31.657704	\N	\N
37	B-20260115-007	6	5	\N	\N	11	2026-01-15	11:00:00	150	13:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:20:17.088948	2026-01-15 14:12:40.760748	2026-01-15 14:12:40.760748	\N	\N
41	B-20260115-009	7	1	2	4	12	2026-01-15	17:00:00	30	17:30:00	confirmed	\N	t	\N	\N	0.00	\N	\N	2026-01-15 06:10:13.336063	2026-01-15 16:21:47.083698	2026-01-15 16:21:47.083698	\N	\N
38	B-20260115-008	6	4	\N	\N	11	2026-01-15	13:00:00	45	13:45:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 14:10:10.93979	2026-01-15 14:51:59.878312	2026-01-15 14:51:59.878312	\N	\N
32	B-20260115-002	6	5	\N	\N	11	2026-01-15	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:17:46.801001	2026-01-15 15:04:19.684136	2026-01-15 15:04:19.684136	\N	\N
31	B-20260115-001	6	5	\N	\N	11	2026-01-15	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:17:44.429298	2026-01-15 15:02:16.335042	2026-01-15 15:02:16.335042	\N	\N
43	BK00820260115063332	7	4	2	1	1	2026-01-25	16:30:00	45	17:15:00	confirmed	\N	f	\N	\N	0.00	ок	\N	2026-01-15 06:33:32.324294	2026-01-15 10:18:57.019638	2026-01-15 10:18:57.019638	\N	\N
45	BK00820260115064233	7	1	3	1	1	2026-01-16	12:00:00	30	12:30:00	confirmed	\N	f	\N	\N	0.00	ок	\N	2026-01-15 06:42:33.110157	2026-01-15 08:40:28.180897	2026-01-15 08:40:28.180897	\N	\N
60	B-20260118-001	10	2	\N	\N	\N	2026-01-18	16:00:00	60	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 14:07:03.885573	2026-01-15 14:07:27.831796	2026-01-15 14:07:27.831796	\N	\N
53	BK00820260115073714	7	4	4	1	1	2026-01-18	17:00:00	45	17:45:00	confirmed	\N	f	\N	\N	0.00	ок	\N	2026-01-15 07:37:14.573525	2026-01-15 14:10:51.567723	2026-01-15 14:10:51.567723	\N	\N
48	B-20260116-002	6	5	\N	\N	11	2026-01-16	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 07:02:17.95854	2026-01-15 14:13:39.523761	2026-01-15 14:13:39.50808	\N	\N
61	B-20260118-002	10	4	\N	\N	\N	2026-01-18	16:00:00	45	16:45:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 14:15:48.124134	2026-01-15 14:18:27.12799	2026-01-15 14:18:27.12799	\N	\N
62	B-20260118-003	11	3	\N	1	\N	2026-01-18	14:30:00	120	16:30:00	completed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 15:05:17.117431	2026-01-15 15:15:40.483955	2026-01-15 15:05:17.121668	2026-01-15 15:15:40.447094	\N
63	B-20260120-001	6	5	3	2	11	2026-01-20	11:00:00	150	13:30:00	completed	3000.00	t	cash	\N	0.00	\N	\N	2026-01-15 15:16:38.992949	2026-01-15 15:17:46.345224	2026-01-15 15:17:11.607934	2026-01-15 15:17:36.354132	\N
64	B-20260121-001	12	1	\N	\N	\N	2026-01-23	17:00:00	30	17:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 15:21:02.567135	2026-01-15 16:22:32.110411	2026-01-15 16:22:32.110411	\N	\N
46	BK00820260115064916	7	1	3	1	1	2026-01-24	16:30:00	30	17:00:00	confirmed	\N	f	\N	\N	0.00	ок	\N	2026-01-15 06:49:16.685128	2026-01-15 10:30:11.997753	2026-01-15 10:30:11.997753	\N	\N
65	BK00820260115164223	6	1	4	1	1	2026-01-17	10:00:00	30	10:30:00	confirmed	\N	f	\N	\N	0.00	не люблю одеколон	\N	2026-01-15 16:42:23.611958	2026-01-15 16:43:43.148314	2026-01-15 16:43:43.142539	\N	\N
\.


--
-- Data for Name: broadcasts; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.broadcasts (id, text, image_path, target_audience, filter_params, status, total_sent, total_errors, created_by, created_at, sent_at) FROM stdin;
\.


--
-- Data for Name: client_history; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.client_history (id, client_id, booking_id, service_id, master_id, date, amount, notes, created_at) FROM stdin;
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.clients (id, user_id, full_name, phone, total_visits, total_amount, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: master_services; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.master_services (id, master_id, service_id, created_at) FROM stdin;
\.


--
-- Data for Name: masters; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.masters (id, user_id, full_name, phone, telegram_id, specialization, is_universal, created_at, updated_at) FROM stdin;
1	\N	Иван Петров	+79991111111	\N	Мужские стрижки	t	2026-01-14 04:11:09.888914	2026-01-14 04:11:09.888914
2	\N	Мария Сидорова	+79992222222	\N	Женские стрижки, окрашивание	t	2026-01-14 04:11:09.888914	2026-01-14 04:11:09.888914
3	\N	Алексей Смирнов	+79993333333	\N	Мужские стрижки, борода	t	2026-01-14 04:11:09.888914	2026-01-14 04:11:09.888914
4	\N	Елена Козлова	+79994444444	\N	Окрашивание, мелирование	t	2026-01-14 04:11:09.888914	2026-01-14 04:11:09.888914
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.notifications (id, user_id, booking_id, notification_type, message, is_sent, sent_at, error_message, created_at) FROM stdin;
\.


--
-- Data for Name: posts; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.posts (id, number, name, description, is_active, created_at, updated_at) FROM stdin;
1	1	Рабочее место 1	Основное рабочее место	t	2026-01-14 04:11:09.890564	2026-01-14 04:11:09.890564
2	2	Рабочее место 2	Дополнительное рабочее место	t	2026-01-14 04:11:09.890564	2026-01-14 04:11:09.890564
3	3	Рабочее место 3	VIP рабочее место	t	2026-01-14 04:11:09.890564	2026-01-14 04:11:09.890564
4	4	Рабочее место 4	Рабочее место для окрашивания	t	2026-01-14 04:11:09.890564	2026-01-14 04:11:09.890564
\.


--
-- Data for Name: promocodes; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.promocodes (id, code, discount_type, discount_value, service_id, min_amount, max_uses, current_uses, start_date, end_date, is_active, description, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: promotions; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.promotions (id, name, description, discount_type, discount_value, service_id, start_date, end_date, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: services; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.services (id, name, description, duration, price, is_active, created_at, updated_at) FROM stdin;
1	Стрижка мужская	Классическая мужская стрижка	30	800.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
2	Стрижка женская	Женская стрижка любой сложности	60	1500.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
3	Окрашивание	Окрашивание волос	120	2500.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
4	Укладка	Укладка волос	45	1000.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
5	Мелирование	Мелирование волос	150	3000.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
\.


--
-- Data for Name: settings; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.settings (id, key, value, description, updated_at) FROM stdin;
\.


--
-- Data for Name: timeslots; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.timeslots (id, date, "time", is_available, booking_id, created_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: tenant_1; Owner: barber_user
--

COPY tenant_1.users (id, telegram_id, username, first_name, last_name, phone, is_admin, is_master, is_blocked, created_at, updated_at, email, role, full_name) FROM stdin;
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: tenant_8; Owner: barber_user
--

COPY tenant_8.bookings (id, booking_number, client_id, service_id, master_id, post_id, created_by, date, "time", duration, end_time, status, amount, is_paid, payment_method, promocode_id, discount_amount, comment, admin_comment, created_at, updated_at, confirmed_at, completed_at, cancelled_at) FROM stdin;
1	BK00820260101001	1	1	1	1	\N	2026-01-01	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
2	BK00820260101002	1	1	1	1	\N	2026-01-01	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
3	BK00820260101003	1	1	1	1	\N	2026-01-01	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
4	BK00820260102001	1	1	1	1	\N	2026-01-02	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
5	BK00820260102002	1	1	1	1	\N	2026-01-02	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
6	BK00820260102003	1	1	1	1	\N	2026-01-02	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
7	BK00820260103001	1	1	1	1	\N	2026-01-03	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
8	BK00820260103002	1	1	1	1	\N	2026-01-03	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
9	BK00820260103003	1	1	1	1	\N	2026-01-03	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
10	BK00820260105001	1	1	1	1	\N	2026-01-05	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
11	BK00820260105002	1	1	1	1	\N	2026-01-05	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
12	BK00820260105003	1	1	1	1	\N	2026-01-05	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
13	BK00820260106001	1	1	1	1	\N	2026-01-06	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
14	BK00820260106002	1	1	1	1	\N	2026-01-06	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
15	BK00820260106003	1	1	1	1	\N	2026-01-06	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
16	BK00820260107001	1	1	1	1	\N	2026-01-07	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
17	BK00820260107002	1	1	1	1	\N	2026-01-07	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
18	BK00820260107003	1	1	1	1	\N	2026-01-07	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
19	BK00820260108001	1	1	1	1	\N	2026-01-08	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
20	BK00820260108002	1	1	1	1	\N	2026-01-08	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
21	BK00820260108003	1	1	1	1	\N	2026-01-08	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
22	BK00820260109001	1	1	1	1	\N	2026-01-09	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
23	BK00820260109002	1	1	1	1	\N	2026-01-09	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
24	BK00820260109003	1	1	1	1	\N	2026-01-09	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
25	BK00820260110001	1	1	1	1	\N	2026-01-10	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
26	BK00820260110002	1	1	1	1	\N	2026-01-10	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
27	BK00820260110003	1	1	1	1	\N	2026-01-10	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
28	BK00820260112001	1	1	1	1	\N	2026-01-12	09:00:00	30	09:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
29	BK00820260112002	1	1	1	1	\N	2026-01-12	10:30:00	30	11:00:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
30	BK00820260112003	1	1	1	1	\N	2026-01-12	12:00:00	30	12:30:00	completed	\N	f	\N	\N	0.00	Тестовая запись	\N	2026-01-14 04:12:12.232615	2026-01-14 04:12:12.232615	\N	\N	\N
35	B-20260115-005	6	5	\N	\N	11	2026-01-15	14:30:00	150	17:00:00	cancelled	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:18:13.457871	2026-01-14 14:55:13.764516	\N	\N	\N
40	B-20260116-001	8	2	4	2	13	2026-01-16	13:30:00	60	14:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 04:55:57.604577	2026-01-15 06:09:24.0553	2026-01-15 06:08:01.614023	\N	\N
34	B-20260115-004	6	5	\N	\N	11	2026-01-15	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:17:49.693194	2026-01-14 14:53:00.830902	\N	\N	\N
36	B-20260115-006	6	5	\N	\N	11	2026-01-15	15:30:00	150	18:00:00	completed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:18:15.860349	2026-01-14 15:31:09.380582	\N	2026-01-14 15:31:09.370942	\N
39	B-20260123-001	7	1	3	1	12	2026-01-23	15:30:00	30	16:00:00	completed	1200.00	t	cash	\N	0.00	\N	\N	2026-01-14 15:09:45.425435	2026-01-15 06:10:21.73395	2026-01-15 06:08:43.981685	2026-01-15 06:09:53.038509	\N
44	BK00820260115063757	7	5	2	4	1	2026-01-16	10:30:00	150	13:00:00	confirmed	\N	f	\N	\N	0.00	ок	\N	2026-01-15 06:37:57.991996	2026-01-15 08:42:19.602735	2026-01-15 08:42:19.602735	\N	\N
33	B-20260115-003	6	5	\N	2	11	2026-01-15	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:17:48.401578	2026-01-15 16:22:09.120645	2026-01-15 16:22:09.120645	\N	\N
47	BK00820260115065326	7	1	2	4	1	2026-01-16	10:00:00	30	10:30:00	cancelled	\N	f	\N	\N	0.00	\N	\N	2026-01-15 06:53:26.969857	2026-01-15 16:48:19.23251	2026-01-15 10:59:26.754951	\N	2026-01-15 16:48:19.144742
49	BK00820260115071652	7	5	4	3	1	2026-01-16	15:00:00	150	17:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 07:16:52.282592	2026-01-15 10:58:54.835527	2026-01-15 10:58:54.835527	\N	\N
42	B-20260131-001	7	1	4	2	12	2026-01-31	17:00:00	30	17:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 06:11:49.918406	2026-01-15 10:31:35.465331	2026-01-15 10:31:26.850495	\N	\N
50	BK00820260115072132	7	4	4	\N	1	2026-01-16	13:00:00	45	13:45:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 07:21:32.850318	2026-01-15 14:12:22.785588	2026-01-15 14:12:22.785588	\N	\N
52	BK00820260115072913	7	4	4	2	1	2026-01-17	14:00:00	45	14:45:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 07:29:13.257947	2026-01-15 14:12:31.657704	2026-01-15 14:12:31.657704	\N	\N
37	B-20260115-007	6	5	\N	\N	11	2026-01-15	11:00:00	150	13:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:20:17.088948	2026-01-15 14:12:40.760748	2026-01-15 14:12:40.760748	\N	\N
41	B-20260115-009	7	1	2	4	12	2026-01-15	17:00:00	30	17:30:00	confirmed	\N	t	\N	\N	0.00	\N	\N	2026-01-15 06:10:13.336063	2026-01-15 16:21:47.083698	2026-01-15 16:21:47.083698	\N	\N
38	B-20260115-008	6	4	\N	\N	11	2026-01-15	13:00:00	45	13:45:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 14:10:10.93979	2026-01-15 14:51:59.878312	2026-01-15 14:51:59.878312	\N	\N
32	B-20260115-002	6	5	\N	\N	11	2026-01-15	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:17:46.801001	2026-01-15 15:04:19.684136	2026-01-15 15:04:19.684136	\N	\N
31	B-20260115-001	6	5	\N	\N	11	2026-01-15	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-14 13:17:44.429298	2026-01-15 15:02:16.335042	2026-01-15 15:02:16.335042	\N	\N
43	BK00820260115063332	7	4	2	1	1	2026-01-25	16:30:00	45	17:15:00	confirmed	\N	f	\N	\N	0.00	ок	\N	2026-01-15 06:33:32.324294	2026-01-15 10:18:57.019638	2026-01-15 10:18:57.019638	\N	\N
45	BK00820260115064233	7	1	3	1	1	2026-01-16	12:00:00	30	12:30:00	confirmed	\N	f	\N	\N	0.00	ок	\N	2026-01-15 06:42:33.110157	2026-01-15 08:40:28.180897	2026-01-15 08:40:28.180897	\N	\N
60	B-20260118-001	10	2	\N	\N	\N	2026-01-18	16:00:00	60	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 14:07:03.885573	2026-01-15 14:07:27.831796	2026-01-15 14:07:27.831796	\N	\N
53	BK00820260115073714	7	4	4	1	1	2026-01-18	17:00:00	45	17:45:00	confirmed	\N	f	\N	\N	0.00	ок	\N	2026-01-15 07:37:14.573525	2026-01-15 14:10:51.567723	2026-01-15 14:10:51.567723	\N	\N
48	B-20260116-002	6	5	\N	\N	11	2026-01-16	14:30:00	150	17:00:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 07:02:17.95854	2026-01-15 14:13:39.523761	2026-01-15 14:13:39.50808	\N	\N
61	B-20260118-002	10	4	\N	\N	\N	2026-01-18	16:00:00	45	16:45:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 14:15:48.124134	2026-01-15 14:18:27.12799	2026-01-15 14:18:27.12799	\N	\N
62	B-20260118-003	11	3	\N	1	\N	2026-01-18	14:30:00	120	16:30:00	completed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 15:05:17.117431	2026-01-15 15:15:40.483955	2026-01-15 15:05:17.121668	2026-01-15 15:15:40.447094	\N
63	B-20260120-001	6	5	3	2	11	2026-01-20	11:00:00	150	13:30:00	completed	3000.00	t	cash	\N	0.00	\N	\N	2026-01-15 15:16:38.992949	2026-01-15 15:17:46.345224	2026-01-15 15:17:11.607934	2026-01-15 15:17:36.354132	\N
64	B-20260121-001	12	1	\N	\N	\N	2026-01-23	17:00:00	30	17:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-15 15:21:02.567135	2026-01-15 16:22:32.110411	2026-01-15 16:22:32.110411	\N	\N
65	BK00820260115164223	6	1	4	1	1	2026-01-17	10:00:00	30	10:30:00	confirmed	\N	f	\N	\N	0.00	не люблю одеколон	\N	2026-01-15 16:42:23.611958	2026-01-15 16:43:43.148314	2026-01-15 16:43:43.142539	\N	\N
46	BK00820260115064916	7	1	3	1	1	2026-01-24	16:30:00	30	17:00:00	cancelled	\N	f	\N	\N	0.00	ок	\N	2026-01-15 06:49:16.685128	2026-01-16 00:21:15.997194	2026-01-15 10:30:11.997753	\N	2026-01-16 00:21:15.99112
66	B-20260119-001	7	3	2	4	\N	2026-01-19	14:30:00	120	16:30:00	confirmed	\N	f	\N	\N	0.00	\N	\N	2026-01-16 07:13:54.620172	2026-01-16 07:23:28.975878	2026-01-16 07:23:28.975878	\N	\N
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: tenant_8; Owner: barber_user
--

COPY tenant_8.clients (id, user_id, full_name, phone, email, telegram_id, notes, created_at, updated_at) FROM stdin;
1	\N	Петр Иванов	+79995555555	petr@example.com	\N	\N	2026-01-14 04:11:09.891956	2026-01-14 04:11:09.891956
2	\N	Анна Смирнова	+79996666666	anna@example.com	\N	\N	2026-01-14 04:11:09.891956	2026-01-14 04:11:09.891956
3	\N	Дмитрий Козлов	+79997777777	dmitry@example.com	\N	\N	2026-01-14 04:11:09.891956	2026-01-14 04:11:09.891956
4	\N	Ольга Новикова	+79998888888	olga@example.com	\N	\N	2026-01-14 04:11:09.891956	2026-01-14 04:11:09.891956
5	\N	Сергей Волков	+79999999999	sergey@example.com	\N	\N	2026-01-14 04:11:09.891956	2026-01-14 04:11:09.891956
6	11	Иван Петров	+79610211760	\N	\N	\N	2026-01-14 13:17:30.559435	2026-01-14 13:17:30.559435
7	12	Кирилл	+79065281940	\N	\N	\N	2026-01-14 15:09:33.865723	2026-01-14 15:09:33.865723
8	13	Комарова Ольга	89605338414	\N	\N	\N	2026-01-15 04:55:49.422843	2026-01-15 04:55:49.422843
9	14	Ванесса Рыжая	+79610245563	\N	\N	\N	2026-01-15 11:10:22.73581	2026-01-15 11:10:22.73581
10	1	Сузанна Рудая	+79991234567	\N	\N	\N	2026-01-15 11:47:51.361288	2026-01-15 11:47:51.361288
11	15	Сузанна Василькович	+79834548845	\N	\N	\N	2026-01-15 15:04:58.882911	2026-01-15 15:04:58.882911
12	16	Василий Гросман	+7989332243	\N	\N	\N	2026-01-15 15:20:44.823662	2026-01-15 15:20:44.823662
\.


--
-- Data for Name: masters; Type: TABLE DATA; Schema: tenant_8; Owner: barber_user
--

COPY tenant_8.masters (id, user_id, full_name, phone, telegram_id, specialization, is_universal, created_at, updated_at) FROM stdin;
1	\N	Иван Петров	+79991111111	\N	Мужские стрижки	t	2026-01-14 04:11:09.888914	2026-01-14 04:11:09.888914
2	\N	Мария Сидорова	+79992222222	\N	Женские стрижки, окрашивание	t	2026-01-14 04:11:09.888914	2026-01-14 04:11:09.888914
3	\N	Алексей Смирнов	+79993333333	\N	Мужские стрижки, борода	t	2026-01-14 04:11:09.888914	2026-01-14 04:11:09.888914
4	\N	Елена Козлова	+79994444444	\N	Окрашивание, мелирование	t	2026-01-14 04:11:09.888914	2026-01-14 04:11:09.888914
\.


--
-- Data for Name: posts; Type: TABLE DATA; Schema: tenant_8; Owner: barber_user
--

COPY tenant_8.posts (id, number, name, description, is_active, created_at, updated_at) FROM stdin;
1	1	Рабочее место 1	Основное рабочее место	t	2026-01-14 04:11:09.890564	2026-01-14 04:11:09.890564
2	2	Рабочее место 2	Дополнительное рабочее место	t	2026-01-14 04:11:09.890564	2026-01-14 04:11:09.890564
3	3	Рабочее место 3	VIP рабочее место	t	2026-01-14 04:11:09.890564	2026-01-14 04:11:09.890564
4	4	Рабочее место 4	Рабочее место для окрашивания	t	2026-01-14 04:11:09.890564	2026-01-14 04:11:09.890564
\.


--
-- Data for Name: services; Type: TABLE DATA; Schema: tenant_8; Owner: barber_user
--

COPY tenant_8.services (id, name, description, duration, price, is_active, created_at, updated_at) FROM stdin;
1	Стрижка мужская	Классическая мужская стрижка	30	800.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
2	Стрижка женская	Женская стрижка любой сложности	60	1500.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
3	Окрашивание	Окрашивание волос	120	2500.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
4	Укладка	Укладка волос	45	1000.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
5	Мелирование	Мелирование волос	150	3000.00	t	2026-01-14 04:11:09.886705	2026-01-14 04:11:09.886705
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: tenant_8; Owner: barber_user
--

COPY tenant_8.users (id, username, email, password_hash, full_name, phone, role, telegram_id, is_active, created_at, updated_at) FROM stdin;
1	test	test@barber-saas.com	$2b$12$iQR6JBY4k0M2zNA6Y1/ZT.NCxlQIH3a12C/3B4kzjfvavloWMAu0G	Тестовый администратор	+79991234567	admin	\N	t	2026-01-14 04:11:09.878513	2026-01-14 04:11:09.878513
11	komarofleo	\N	04694bd9566503b2b12055d1ba616dd565cb2fdf532ee40729262f800573b115	Leonid Komarov	\N	admin	329621295	t	2026-01-14 12:41:19.192678	2026-01-14 12:41:19.192678
12	Viitto_o	\N	e047b1c2965539bf45a1fa620239c843984de347a9bd9409a1f7460d0ba43adf	Кирилл	\N	client	406407955	t	2026-01-14 15:09:17.96079	2026-01-14 15:09:17.96079
13	okomarova	\N	09ad589e501a4eef08ef0c509fa8cf065a43ff9e9322580e41f9ec7a9ae292da	Ольга	\N	client	340867013	t	2026-01-15 04:36:44.165391	2026-01-15 04:36:44.165391
14	79610245563	79610245563@temp.local		Ванесса Рыжая	+79610245563	client	\N	t	2026-01-15 11:10:22.699148	2026-01-15 11:10:22.69915
15	79834548845	79834548845@temp.local		Сузанна Василькович	+79834548845	client	\N	t	2026-01-15 15:04:58.874729	2026-01-15 15:04:58.874733
16	7989332243	7989332243@temp.local		Василий Гросман	+7989332243	client	\N	t	2026-01-15 15:20:44.748353	2026-01-15 15:20:44.748362
\.


--
-- Name: blocked_slots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.blocked_slots_id_seq', 1, false);


--
-- Name: booking_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.booking_history_id_seq', 1, false);


--
-- Name: bookings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.bookings_id_seq', 1, false);


--
-- Name: broadcasts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.broadcasts_id_seq', 1, false);


--
-- Name: client_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.client_history_id_seq', 1, false);


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.clients_id_seq', 1, true);


--
-- Name: companies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.companies_id_seq', 11, true);


--
-- Name: master_services_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.master_services_id_seq', 1, false);


--
-- Name: masters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.masters_id_seq', 1, false);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.notifications_id_seq', 1, false);


--
-- Name: payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.payments_id_seq', 1, false);


--
-- Name: plans_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.plans_id_seq', 6, true);


--
-- Name: posts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.posts_id_seq', 1, false);


--
-- Name: promocodes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.promocodes_id_seq', 1, false);


--
-- Name: promotions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.promotions_id_seq', 1, false);


--
-- Name: services_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.services_id_seq', 1, false);


--
-- Name: settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.settings_id_seq', 1, false);


--
-- Name: subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.subscriptions_id_seq', 8, true);


--
-- Name: super_admins_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.super_admins_id_seq', 2, true);


--
-- Name: timeslots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.timeslots_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: barber_user
--

SELECT pg_catalog.setval('public.users_id_seq', 1, true);


--
-- Name: bookings_id_seq; Type: SEQUENCE SET; Schema: tenant_8; Owner: barber_user
--

SELECT pg_catalog.setval('tenant_8.bookings_id_seq', 66, true);


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: tenant_8; Owner: barber_user
--

SELECT pg_catalog.setval('tenant_8.clients_id_seq', 12, true);


--
-- Name: masters_id_seq; Type: SEQUENCE SET; Schema: tenant_8; Owner: barber_user
--

SELECT pg_catalog.setval('tenant_8.masters_id_seq', 4, true);


--
-- Name: posts_id_seq; Type: SEQUENCE SET; Schema: tenant_8; Owner: barber_user
--

SELECT pg_catalog.setval('tenant_8.posts_id_seq', 4, true);


--
-- Name: services_id_seq; Type: SEQUENCE SET; Schema: tenant_8; Owner: barber_user
--

SELECT pg_catalog.setval('tenant_8.services_id_seq', 5, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: tenant_8; Owner: barber_user
--

SELECT pg_catalog.setval('tenant_8.users_id_seq', 16, true);


--
-- Name: blocked_slots blocked_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.blocked_slots
    ADD CONSTRAINT blocked_slots_pkey PRIMARY KEY (id);


--
-- Name: booking_history booking_history_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.booking_history
    ADD CONSTRAINT booking_history_pkey PRIMARY KEY (id);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (id);


--
-- Name: broadcasts broadcasts_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.broadcasts
    ADD CONSTRAINT broadcasts_pkey PRIMARY KEY (id);


--
-- Name: client_history client_history_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.client_history
    ADD CONSTRAINT client_history_pkey PRIMARY KEY (id);


--
-- Name: clients clients_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_pkey PRIMARY KEY (id);


--
-- Name: companies companies_api_key_key; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_api_key_key UNIQUE (api_key);


--
-- Name: companies companies_email_key; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_email_key UNIQUE (email);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: companies companies_telegram_bot_token_key; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_telegram_bot_token_key UNIQUE (telegram_bot_token);


--
-- Name: master_services master_services_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.master_services
    ADD CONSTRAINT master_services_pkey PRIMARY KEY (id);


--
-- Name: masters masters_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.masters
    ADD CONSTRAINT masters_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: payments payments_yookassa_payment_id_key; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_yookassa_payment_id_key UNIQUE (yookassa_payment_id);


--
-- Name: plans plans_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.plans
    ADD CONSTRAINT plans_pkey PRIMARY KEY (id);


--
-- Name: posts posts_number_key; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_number_key UNIQUE (number);


--
-- Name: posts posts_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT posts_pkey PRIMARY KEY (id);


--
-- Name: promocodes promocodes_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.promocodes
    ADD CONSTRAINT promocodes_pkey PRIMARY KEY (id);


--
-- Name: promotions promotions_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.promotions
    ADD CONSTRAINT promotions_pkey PRIMARY KEY (id);


--
-- Name: services services_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.services
    ADD CONSTRAINT services_pkey PRIMARY KEY (id);


--
-- Name: settings settings_key_key; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_key_key UNIQUE (key);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: super_admins super_admins_email_key; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.super_admins
    ADD CONSTRAINT super_admins_email_key UNIQUE (email);


--
-- Name: super_admins super_admins_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.super_admins
    ADD CONSTRAINT super_admins_pkey PRIMARY KEY (id);


--
-- Name: super_admins super_admins_telegram_id_key; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.super_admins
    ADD CONSTRAINT super_admins_telegram_id_key UNIQUE (telegram_id);


--
-- Name: super_admins super_admins_username_key; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.super_admins
    ADD CONSTRAINT super_admins_username_key UNIQUE (username);


--
-- Name: timeslots timeslots_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.timeslots
    ADD CONSTRAINT timeslots_pkey PRIMARY KEY (id);


--
-- Name: master_services uq_master_service; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.master_services
    ADD CONSTRAINT uq_master_service UNIQUE (master_id, service_id);


--
-- Name: timeslots uq_timeslot_date_time; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.timeslots
    ADD CONSTRAINT uq_timeslot_date_time UNIQUE (date, "time");


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: bookings bookings_booking_number_key; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.bookings
    ADD CONSTRAINT bookings_booking_number_key UNIQUE (booking_number);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (id);


--
-- Name: clients clients_pkey; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.clients
    ADD CONSTRAINT clients_pkey PRIMARY KEY (id);


--
-- Name: masters masters_pkey; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.masters
    ADD CONSTRAINT masters_pkey PRIMARY KEY (id);


--
-- Name: masters masters_user_id_key; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.masters
    ADD CONSTRAINT masters_user_id_key UNIQUE (user_id);


--
-- Name: posts posts_number_key; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.posts
    ADD CONSTRAINT posts_number_key UNIQUE (number);


--
-- Name: posts posts_pkey; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.posts
    ADD CONSTRAINT posts_pkey PRIMARY KEY (id);


--
-- Name: services services_pkey; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.services
    ADD CONSTRAINT services_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_blocks_dates; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_blocks_dates ON public.blocked_slots USING btree (start_date, end_date);


--
-- Name: idx_bookings_date_status; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_bookings_date_status ON public.bookings USING btree (date, status);


--
-- Name: idx_bookings_date_time; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_bookings_date_time ON public.bookings USING btree (date, "time");


--
-- Name: idx_companies_email; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_companies_email ON public.companies USING btree (email);


--
-- Name: idx_companies_is_active; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_companies_is_active ON public.companies USING btree (is_active);


--
-- Name: idx_companies_name; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_companies_name ON public.companies USING btree (name);


--
-- Name: idx_companies_plan_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_companies_plan_id ON public.companies USING btree (plan_id);


--
-- Name: idx_companies_subscription_status; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_companies_subscription_status ON public.companies USING btree (subscription_status);


--
-- Name: idx_payments_company_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_payments_company_id ON public.payments USING btree (company_id);


--
-- Name: idx_payments_plan_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_payments_plan_id ON public.payments USING btree (plan_id);


--
-- Name: idx_payments_status; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_payments_status ON public.payments USING btree (status);


--
-- Name: idx_payments_subscription_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_payments_subscription_id ON public.payments USING btree (subscription_id);


--
-- Name: idx_payments_yookassa_payment_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_payments_yookassa_payment_id ON public.payments USING btree (yookassa_payment_id);


--
-- Name: idx_promocodes_active_dates; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_promocodes_active_dates ON public.promocodes USING btree (is_active, start_date, end_date);


--
-- Name: idx_promotions_dates; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_promotions_dates ON public.promotions USING btree (start_date, end_date);


--
-- Name: idx_subscriptions_company_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_subscriptions_company_id ON public.subscriptions USING btree (company_id);


--
-- Name: idx_subscriptions_end_date; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_subscriptions_end_date ON public.subscriptions USING btree (end_date);


--
-- Name: idx_subscriptions_plan_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_subscriptions_plan_id ON public.subscriptions USING btree (plan_id);


--
-- Name: idx_subscriptions_status; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_subscriptions_status ON public.subscriptions USING btree (status);


--
-- Name: idx_timeslots_date_available; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX idx_timeslots_date_available ON public.timeslots USING btree (date, is_available);


--
-- Name: ix_blocked_slots_block_type; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_blocked_slots_block_type ON public.blocked_slots USING btree (block_type);


--
-- Name: ix_blocked_slots_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_blocked_slots_id ON public.blocked_slots USING btree (id);


--
-- Name: ix_blocked_slots_master_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_blocked_slots_master_id ON public.blocked_slots USING btree (master_id);


--
-- Name: ix_blocked_slots_post_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_blocked_slots_post_id ON public.blocked_slots USING btree (post_id);


--
-- Name: ix_blocked_slots_service_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_blocked_slots_service_id ON public.blocked_slots USING btree (service_id);


--
-- Name: ix_blocked_slots_start_date; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_blocked_slots_start_date ON public.blocked_slots USING btree (start_date);


--
-- Name: ix_booking_history_booking_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_booking_history_booking_id ON public.booking_history USING btree (booking_id);


--
-- Name: ix_booking_history_changed_at; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_booking_history_changed_at ON public.booking_history USING btree (changed_at);


--
-- Name: ix_booking_history_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_booking_history_id ON public.booking_history USING btree (id);


--
-- Name: ix_bookings_booking_number; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE UNIQUE INDEX ix_bookings_booking_number ON public.bookings USING btree (booking_number);


--
-- Name: ix_bookings_client_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_bookings_client_id ON public.bookings USING btree (client_id);


--
-- Name: ix_bookings_date; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_bookings_date ON public.bookings USING btree (date);


--
-- Name: ix_bookings_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_bookings_id ON public.bookings USING btree (id);


--
-- Name: ix_bookings_master_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_bookings_master_id ON public.bookings USING btree (master_id);


--
-- Name: ix_bookings_post_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_bookings_post_id ON public.bookings USING btree (post_id);


--
-- Name: ix_bookings_service_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_bookings_service_id ON public.bookings USING btree (service_id);


--
-- Name: ix_bookings_status; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_bookings_status ON public.bookings USING btree (status);


--
-- Name: ix_broadcasts_created_at; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_broadcasts_created_at ON public.broadcasts USING btree (created_at);


--
-- Name: ix_broadcasts_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_broadcasts_id ON public.broadcasts USING btree (id);


--
-- Name: ix_broadcasts_status; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_broadcasts_status ON public.broadcasts USING btree (status);


--
-- Name: ix_client_history_client_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_client_history_client_id ON public.client_history USING btree (client_id);


--
-- Name: ix_client_history_date; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_client_history_date ON public.client_history USING btree (date);


--
-- Name: ix_client_history_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_client_history_id ON public.client_history USING btree (id);


--
-- Name: ix_clients_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_clients_id ON public.clients USING btree (id);


--
-- Name: ix_clients_phone; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_clients_phone ON public.clients USING btree (phone);


--
-- Name: ix_clients_user_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE UNIQUE INDEX ix_clients_user_id ON public.clients USING btree (user_id);


--
-- Name: ix_master_services_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_master_services_id ON public.master_services USING btree (id);


--
-- Name: ix_master_services_master_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_master_services_master_id ON public.master_services USING btree (master_id);


--
-- Name: ix_master_services_service_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_master_services_service_id ON public.master_services USING btree (service_id);


--
-- Name: ix_masters_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_masters_id ON public.masters USING btree (id);


--
-- Name: ix_masters_telegram_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_masters_telegram_id ON public.masters USING btree (telegram_id);


--
-- Name: ix_masters_user_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE UNIQUE INDEX ix_masters_user_id ON public.masters USING btree (user_id);


--
-- Name: ix_notifications_booking_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_notifications_booking_id ON public.notifications USING btree (booking_id);


--
-- Name: ix_notifications_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_notifications_id ON public.notifications USING btree (id);


--
-- Name: ix_notifications_is_sent; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_notifications_is_sent ON public.notifications USING btree (is_sent);


--
-- Name: ix_notifications_notification_type; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_notifications_notification_type ON public.notifications USING btree (notification_type);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_posts_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_posts_id ON public.posts USING btree (id);


--
-- Name: ix_promocodes_code; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE UNIQUE INDEX ix_promocodes_code ON public.promocodes USING btree (code);


--
-- Name: ix_promocodes_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_promocodes_id ON public.promocodes USING btree (id);


--
-- Name: ix_promocodes_is_active; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_promocodes_is_active ON public.promocodes USING btree (is_active);


--
-- Name: ix_promotions_end_date; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_promotions_end_date ON public.promotions USING btree (end_date);


--
-- Name: ix_promotions_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_promotions_id ON public.promotions USING btree (id);


--
-- Name: ix_promotions_is_active; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_promotions_is_active ON public.promotions USING btree (is_active);


--
-- Name: ix_promotions_start_date; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_promotions_start_date ON public.promotions USING btree (start_date);


--
-- Name: ix_public_payments_company_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_payments_company_id ON public.payments USING btree (company_id);


--
-- Name: ix_public_payments_plan_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_payments_plan_id ON public.payments USING btree (plan_id);


--
-- Name: ix_public_payments_status; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_payments_status ON public.payments USING btree (status);


--
-- Name: ix_public_payments_subscription_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_payments_subscription_id ON public.payments USING btree (subscription_id);


--
-- Name: ix_public_payments_yookassa_payment_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE UNIQUE INDEX ix_public_payments_yookassa_payment_id ON public.payments USING btree (yookassa_payment_id);


--
-- Name: ix_public_plans_is_active; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_plans_is_active ON public.plans USING btree (is_active);


--
-- Name: ix_public_plans_name; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE UNIQUE INDEX ix_public_plans_name ON public.plans USING btree (name);


--
-- Name: ix_public_subscriptions_company_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_subscriptions_company_id ON public.subscriptions USING btree (company_id);


--
-- Name: ix_public_subscriptions_end_date; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_subscriptions_end_date ON public.subscriptions USING btree (end_date);


--
-- Name: ix_public_subscriptions_plan_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_subscriptions_plan_id ON public.subscriptions USING btree (plan_id);


--
-- Name: ix_public_subscriptions_start_date; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_subscriptions_start_date ON public.subscriptions USING btree (start_date);


--
-- Name: ix_public_subscriptions_status; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_subscriptions_status ON public.subscriptions USING btree (status);


--
-- Name: ix_public_super_admins_email; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE UNIQUE INDEX ix_public_super_admins_email ON public.super_admins USING btree (email);


--
-- Name: ix_public_super_admins_is_active; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_public_super_admins_is_active ON public.super_admins USING btree (is_active);


--
-- Name: ix_public_super_admins_username; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE UNIQUE INDEX ix_public_super_admins_username ON public.super_admins USING btree (username);


--
-- Name: ix_services_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_services_id ON public.services USING btree (id);


--
-- Name: ix_services_is_active; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_services_is_active ON public.services USING btree (is_active);


--
-- Name: ix_settings_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_settings_id ON public.settings USING btree (id);


--
-- Name: ix_timeslots_date; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_timeslots_date ON public.timeslots USING btree (date);


--
-- Name: ix_timeslots_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_timeslots_id ON public.timeslots USING btree (id);


--
-- Name: ix_timeslots_is_available; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_timeslots_is_available ON public.timeslots USING btree (is_available);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_phone; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE INDEX ix_users_phone ON public.users USING btree (phone);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: barber_user
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: idx_tenant_1_users_email; Type: INDEX; Schema: tenant_1; Owner: barber_user
--

CREATE INDEX idx_tenant_1_users_email ON tenant_1.users USING btree (email);


--
-- Name: blocked_slots blocked_slots_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.blocked_slots
    ADD CONSTRAINT blocked_slots_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: blocked_slots blocked_slots_master_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.blocked_slots
    ADD CONSTRAINT blocked_slots_master_id_fkey FOREIGN KEY (master_id) REFERENCES public.masters(id) ON DELETE CASCADE;


--
-- Name: blocked_slots blocked_slots_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.blocked_slots
    ADD CONSTRAINT blocked_slots_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE CASCADE;


--
-- Name: blocked_slots blocked_slots_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.blocked_slots
    ADD CONSTRAINT blocked_slots_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE CASCADE;


--
-- Name: booking_history booking_history_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.booking_history
    ADD CONSTRAINT booking_history_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: booking_history booking_history_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.booking_history
    ADD CONSTRAINT booking_history_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE;


--
-- Name: bookings bookings_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_master_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_master_id_fkey FOREIGN KEY (master_id) REFERENCES public.masters(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.posts(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_promocode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_promocode_id_fkey FOREIGN KEY (promocode_id) REFERENCES public.promocodes(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE SET NULL;


--
-- Name: broadcasts broadcasts_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.broadcasts
    ADD CONSTRAINT broadcasts_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: client_history client_history_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.client_history
    ADD CONSTRAINT client_history_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: client_history client_history_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.client_history
    ADD CONSTRAINT client_history_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE;


--
-- Name: client_history client_history_master_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.client_history
    ADD CONSTRAINT client_history_master_id_fkey FOREIGN KEY (master_id) REFERENCES public.masters(id) ON DELETE SET NULL;


--
-- Name: client_history client_history_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.client_history
    ADD CONSTRAINT client_history_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE SET NULL;


--
-- Name: clients clients_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: companies companies_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id) ON DELETE SET NULL;


--
-- Name: master_services master_services_master_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.master_services
    ADD CONSTRAINT master_services_master_id_fkey FOREIGN KEY (master_id) REFERENCES public.masters(id) ON DELETE CASCADE;


--
-- Name: master_services master_services_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.master_services
    ADD CONSTRAINT master_services_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE CASCADE;


--
-- Name: masters masters_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.masters
    ADD CONSTRAINT masters_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: payments payments_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE SET NULL;


--
-- Name: payments payments_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id);


--
-- Name: payments payments_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscriptions(id);


--
-- Name: promocodes promocodes_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.promocodes
    ADD CONSTRAINT promocodes_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE CASCADE;


--
-- Name: promotions promotions_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.promotions
    ADD CONSTRAINT promotions_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id) ON DELETE CASCADE;


--
-- Name: subscriptions subscriptions_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: subscriptions subscriptions_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id);


--
-- Name: timeslots timeslots_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: barber_user
--

ALTER TABLE ONLY public.timeslots
    ADD CONSTRAINT timeslots_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_client_id_fkey; Type: FK CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.bookings
    ADD CONSTRAINT bookings_client_id_fkey FOREIGN KEY (client_id) REFERENCES tenant_8.clients(id) ON DELETE CASCADE;


--
-- Name: bookings bookings_created_by_fkey; Type: FK CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.bookings
    ADD CONSTRAINT bookings_created_by_fkey FOREIGN KEY (created_by) REFERENCES tenant_8.users(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_master_id_fkey; Type: FK CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.bookings
    ADD CONSTRAINT bookings_master_id_fkey FOREIGN KEY (master_id) REFERENCES tenant_8.masters(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_post_id_fkey; Type: FK CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.bookings
    ADD CONSTRAINT bookings_post_id_fkey FOREIGN KEY (post_id) REFERENCES tenant_8.posts(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_service_id_fkey; Type: FK CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.bookings
    ADD CONSTRAINT bookings_service_id_fkey FOREIGN KEY (service_id) REFERENCES tenant_8.services(id) ON DELETE SET NULL;


--
-- Name: clients clients_user_id_fkey; Type: FK CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.clients
    ADD CONSTRAINT clients_user_id_fkey FOREIGN KEY (user_id) REFERENCES tenant_8.users(id) ON DELETE CASCADE;


--
-- Name: masters masters_user_id_fkey; Type: FK CONSTRAINT; Schema: tenant_8; Owner: barber_user
--

ALTER TABLE ONLY tenant_8.masters
    ADD CONSTRAINT masters_user_id_fkey FOREIGN KEY (user_id) REFERENCES tenant_8.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 6WqsbBS0D3gP1bf3LLp3tFab9Rc35WrSr8OR6FGPHmmTkWZrklrlBmrnhOLe3Ke

