-- ============================================================
-- SCHEMA PostgreSQL — Projet ETL Immobilier
-- Master Data & IA M1 — Ynov 2025-2026
-- ============================================================

-- ── Schéma opérationnel ────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS operationnel;
SET search_path TO operationnel;

-- ── Table centrale : référentiel géographique ──────────────
CREATE TABLE IF NOT EXISTS operationnel.communes (
    id_ville        INTEGER PRIMARY KEY,
    departement     CHAR(3)         NOT NULL,
    ville           VARCHAR(100)    NOT NULL,
    latitude        FLOAT,
    longitude       FLOAT,
    code_insee      CHAR(5),
    code_region     VARCHAR(3)
);

-- ── Données démographiques (geo.api.gouv.fr) ───────────────
CREATE TABLE IF NOT EXISTS operationnel.demographics (
    id              SERIAL PRIMARY KEY,
    id_ville        INTEGER         NOT NULL REFERENCES operationnel.communes(id_ville),
    code_insee      CHAR(5),
    code_region     VARCHAR(3),
    nom_region      VARCHAR(100),
    population      INTEGER,
    superficie_km2  FLOAT,
    densite         FLOAT,
    UNIQUE (id_ville)
);

CREATE INDEX IF NOT EXISTS idx_demographics_id_ville ON operationnel.demographics(id_ville);

-- ── Transactions immobilières (DVF) ────────────────────────
CREATE TABLE IF NOT EXISTS operationnel.transactions (
    id_transaction      INTEGER PRIMARY KEY,
    id_ville            INTEGER         NOT NULL REFERENCES operationnel.communes(id_ville),
    date_transaction    DATE            NOT NULL,
    annee               INTEGER         NOT NULL,
    prix                FLOAT           NOT NULL,
    prix_m2             FLOAT           NOT NULL,
    type_batiment       VARCHAR(20)     NOT NULL,
    surface_habitable   INTEGER         NOT NULL,
    n_pieces            INTEGER,
    vefa                BOOLEAN         DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_transactions_id_ville ON operationnel.transactions(id_ville);
CREATE INDEX IF NOT EXISTS idx_transactions_annee    ON operationnel.transactions(annee);

-- ── Loyers médians par commune et année ────────────────────
CREATE TABLE IF NOT EXISTS operationnel.loyers (
    id              SERIAL PRIMARY KEY,
    id_ville        INTEGER     NOT NULL REFERENCES operationnel.communes(id_ville),
    annee           INTEGER     NOT NULL,
    loyer_m2_appartement    FLOAT,
    loyer_m2_maison         FLOAT,
    loyer_m2_moyen          FLOAT,
    UNIQUE (id_ville, annee)
);

CREATE INDEX IF NOT EXISTS idx_loyers_id_ville ON operationnel.loyers(id_ville);

-- ── Foyers fiscaux par commune et année ────────────────────
CREATE TABLE IF NOT EXISTS operationnel.foyers_fiscaux (
    id                      SERIAL PRIMARY KEY,
    id_ville                INTEGER     NOT NULL REFERENCES operationnel.communes(id_ville),
    annee                   INTEGER     NOT NULL,
    revenu_fiscal_moyen     FLOAT,
    montant_impot_moyen     FLOAT,
    n_foyers_fiscaux        FLOAT,
    UNIQUE (id_ville, annee)
);

CREATE INDEX IF NOT EXISTS idx_foyers_fiscaux_id_ville ON operationnel.foyers_fiscaux(id_ville);

-- ── Parc immobilier par commune et année ───────────────────
CREATE TABLE IF NOT EXISTS operationnel.parc_immobilier (
    id                      SERIAL PRIMARY KEY,
    id_ville                INTEGER     NOT NULL REFERENCES operationnel.communes(id_ville),
    annee                   INTEGER     NOT NULL,
    n_logements             FLOAT,
    n_logements_vacants     FLOAT,
    taux_vacance            FLOAT,
    UNIQUE (id_ville, annee)
);

CREATE INDEX IF NOT EXISTS idx_parc_immobilier_id_ville ON operationnel.parc_immobilier(id_ville);

-- ── Indicateurs macro nationaux (mensuel) ──────────────────
CREATE TABLE IF NOT EXISTS operationnel.indicateurs_macro (
    id                  SERIAL PRIMARY KEY,
    annee               INTEGER     NOT NULL,
    mois                INTEGER,
    taux_interet        FLOAT,
    flux_emprunts_me    FLOAT,
    taux_endettement    FLOAT,
    irl                 FLOAT,
    UNIQUE (annee, mois)
);

-- ── Score d'attractivité par commune (table finale) ────────
CREATE TABLE IF NOT EXISTS operationnel.score_attractivite (
    id                      SERIAL PRIMARY KEY,
    id_ville                INTEGER     NOT NULL REFERENCES operationnel.communes(id_ville),
    annee_ref               INTEGER     NOT NULL,
    prix_m2_median          FLOAT,
    loyer_m2_moyen          FLOAT,
    revenu_fiscal_moyen     FLOAT,
    rendement_brut          FLOAT,
    taux_vacance            FLOAT,
    ratio_effort_fiscal     FLOAT,
    score_rendement         FLOAT,
    score_effort            FLOAT,
    score_richesse          FLOAT,
    score_vacance           FLOAT,
    score_attractivite      FLOAT,
    n_transactions          INTEGER,
    UNIQUE (id_ville, annee_ref)
);

CREATE INDEX IF NOT EXISTS idx_score_id_ville       ON operationnel.score_attractivite(id_ville);
CREATE INDEX IF NOT EXISTS idx_score_attractivite   ON operationnel.score_attractivite(score_attractivite DESC);