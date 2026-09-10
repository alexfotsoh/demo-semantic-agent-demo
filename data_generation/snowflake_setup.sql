-- Setup Snowflake pour le jeu de données "facturation énergie".
-- Adapter les noms de base / schéma / warehouse à votre environnement.

CREATE DATABASE IF NOT EXISTS DEMO_ENERGIE;
CREATE SCHEMA   IF NOT EXISTS DEMO_ENERGIE.RAW;
USE SCHEMA DEMO_ENERGIE.RAW;

CREATE OR REPLACE FILE FORMAT csv_fr
    TYPE = CSV
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    EMPTY_FIELD_AS_NULL = TRUE
    NULL_IF = ('', 'NULL');

CREATE OR REPLACE STAGE stg_energie FILE_FORMAT = csv_fr;
-- PUT file:///chemin/vers/dataset/*.csv @stg_energie;   (via SnowSQL)
-- ou upload manuel depuis Snowsight.

CREATE OR REPLACE TABLE contrats (
    contract_id           VARCHAR(20)   NOT NULL,
    customer_id           VARCHAR(20)   NOT NULL,
    offer_code            VARCHAR(10)   NOT NULL,  -- BASE / HPHC / VERTE / PRO
    region                VARCHAR(60),
    start_date            DATE          NOT NULL,
    end_date              DATE,                    -- NULL = contrat actif
    estimated_annual_kwh  NUMBER(10,0),
    is_internal           BOOLEAN       NOT NULL
);

CREATE OR REPLACE TABLE releves (
    reading_id     VARCHAR(20)   NOT NULL,
    contract_id    VARCHAR(20)   NOT NULL,
    reading_date   DATE          NOT NULL,
    period_start   DATE          NOT NULL,
    period_end     DATE          NOT NULL,
    kwh            NUMBER(12,1)  NOT NULL,
    reading_type   VARCHAR(10)   NOT NULL   -- REEL / ESTIME
);

CREATE OR REPLACE TABLE factures (
    invoice_id          VARCHAR(20)   NOT NULL,
    contract_id         VARCHAR(20)   NOT NULL,
    invoice_type        VARCHAR(20)   NOT NULL,  -- NORMALE / REGULARISATION / AVOIR
    issue_date          DATE          NOT NULL,  -- date d'émission
    period_start        DATE          NOT NULL,  -- début de la période couverte
    period_end          DATE          NOT NULL,  -- fin de la période couverte
    amount_ht           NUMBER(12,2)  NOT NULL,
    vat_amount          NUMBER(12,2)  NOT NULL,
    amount_ttc          NUMBER(12,2)  NOT NULL,
    related_invoice_id  VARCHAR(20)              -- renseigné pour les avoirs
);

CREATE OR REPLACE TABLE lignes_facture (
    line_id      VARCHAR(20)   NOT NULL,
    invoice_id   VARCHAR(20)   NOT NULL,
    line_type    VARCHAR(20)   NOT NULL,  -- ABONNEMENT / CONSO / REMISE / AVOIR
    kwh          NUMBER(12,1),
    unit_price   NUMBER(10,4),
    amount_ht    NUMBER(12,2)  NOT NULL
);

COPY INTO contrats        FROM @stg_energie/contrats.csv        FILE_FORMAT = csv_fr;
COPY INTO releves         FROM @stg_energie/releves.csv         FILE_FORMAT = csv_fr;
COPY INTO factures        FROM @stg_energie/factures.csv        FILE_FORMAT = csv_fr;
COPY INTO lignes_facture  FROM @stg_energie/lignes_facture.csv  FILE_FORMAT = csv_fr;

-- Contrôle rapide : l'écart que la question « combien on a facturé en janvier ? »
-- doit faire apparaître.
SELECT
    SUM(CASE WHEN YEAR(issue_date) = 2025 AND MONTH(issue_date) = 1
             THEN amount_ht END)                                  AS par_date_emission,
    SUM(CASE WHEN DATE '2025-01-01' BETWEEN period_start AND period_end
             THEN amount_ht END)                                  AS par_periode_couverte
FROM factures;
