--
-- PostgreSQL database dump
--

\restrict HqNOYdfFP9qL7XacAXvEj99GA5pGKfYgk1zq6zzw8AiwmhJTnlwayzh8ccImZzJ

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: decision_records; Type: TABLE; Schema: public; Owner: ids_user
--

CREATE TABLE public.decision_records (
    id character varying(64) NOT NULL,
    title character varying(255) NOT NULL,
    status character varying(50) NOT NULL,
    weighted_score numeric(5,2) NOT NULL,
    risk_level character varying(50) NOT NULL,
    recommendation text NOT NULL,
    breakdown jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.decision_records OWNER TO ids_user;

--
-- Name: notebook_sources; Type: TABLE; Schema: public; Owner: ids_user
--

CREATE TABLE public.notebook_sources (
    id character varying(64) NOT NULL,
    title character varying(255) NOT NULL,
    source_type character varying(50) NOT NULL,
    content_hash character varying(64) NOT NULL,
    word_count integer NOT NULL,
    summary text,
    audio_script text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.notebook_sources OWNER TO ids_user;

--
-- Data for Name: decision_records; Type: TABLE DATA; Schema: public; Owner: ids_user
--

COPY public.decision_records (id, title, status, weighted_score, risk_level, recommendation, breakdown, created_at) FROM stdin;
\.


--
-- Data for Name: notebook_sources; Type: TABLE DATA; Schema: public; Owner: ids_user
--

COPY public.notebook_sources (id, title, source_type, content_hash, word_count, summary, audio_script, created_at) FROM stdin;
\.


--
-- Name: decision_records decision_records_pkey; Type: CONSTRAINT; Schema: public; Owner: ids_user
--

ALTER TABLE ONLY public.decision_records
    ADD CONSTRAINT decision_records_pkey PRIMARY KEY (id);


--
-- Name: notebook_sources notebook_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: ids_user
--

ALTER TABLE ONLY public.notebook_sources
    ADD CONSTRAINT notebook_sources_pkey PRIMARY KEY (id);


--
-- Name: idx_decision_records_created; Type: INDEX; Schema: public; Owner: ids_user
--

CREATE INDEX idx_decision_records_created ON public.decision_records USING btree (created_at DESC);


--
-- Name: idx_notebook_sources_hash; Type: INDEX; Schema: public; Owner: ids_user
--

CREATE INDEX idx_notebook_sources_hash ON public.notebook_sources USING btree (content_hash);


--
-- PostgreSQL database dump complete
--

\unrestrict HqNOYdfFP9qL7XacAXvEj99GA5pGKfYgk1zq6zzw8AiwmhJTnlwayzh8ccImZzJ

