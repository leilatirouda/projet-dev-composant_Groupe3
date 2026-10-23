-- =============================================================
-- Groupe 3 SI - Projet composants et services web 2026
-- Base de référence : structures sanitaires (données fictives)
-- Exécuté automatiquement par PostgreSQL au premier démarrage
-- (montage dans /docker-entrypoint-initdb.d)
-- =============================================================

CREATE TABLE IF NOT EXISTS structures_sanitaires (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20)  NOT NULL UNIQUE,
    nom             VARCHAR(150) NOT NULL,
    type            VARCHAR(20)  NOT NULL
                    CHECK (type IN ('CHU', 'CHR', 'CMA', 'CM', 'CSPS', 'CLINIQUE', 'DISPENSAIRE', 'MATERNITE')),
    statut          VARCHAR(20)  NOT NULL
                    CHECK (statut IN ('PUBLIC', 'PRIVE', 'CONFESSIONNEL', 'COMMUNAUTAIRE')),
    region          VARCHAR(60)  NOT NULL,
    province        VARCHAR(60)  NOT NULL,
    district        VARCHAR(80)  NOT NULL,
    commune         VARCHAR(80)  NOT NULL,
    adresse         VARCHAR(200),
    telephone       VARCHAR(20),
    email           VARCHAR(120),
    capacite_lits   INTEGER      NOT NULL DEFAULT 0 CHECK (capacite_lits >= 0),
    services        TEXT[]       NOT NULL DEFAULT '{}',
    latitude        NUMERIC(9,6) CHECK (latitude BETWEEN -90 AND 90),
    longitude       NUMERIC(9,6) CHECK (longitude BETWEEN -180 AND 180),
    date_ouverture  DATE,
    actif           BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Index pour les filtres et la recherche exposés par l'API
CREATE INDEX IF NOT EXISTS idx_structures_region   ON structures_sanitaires (region);
CREATE INDEX IF NOT EXISTS idx_structures_type     ON structures_sanitaires (type);
CREATE INDEX IF NOT EXISTS idx_structures_district ON structures_sanitaires (district);
CREATE INDEX IF NOT EXISTS idx_structures_nom      ON structures_sanitaires (LOWER(nom));

COMMENT ON TABLE  structures_sanitaires IS 'Structures sanitaires fictives exposées par l''API Structures (WSO2 API Manager)';
COMMENT ON COLUMN structures_sanitaires.code IS 'Identifiant métier unique, ex. CSPS-0001';
COMMENT ON COLUMN structures_sanitaires.capacite_lits IS 'Exposé uniquement en v2';
COMMENT ON COLUMN structures_sanitaires.services IS 'Exposé uniquement en v2';
