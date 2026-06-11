-- JobFinding Database Schema
-- Executed after init.sql extensions

-- ============================================
-- Tabla: sources
-- Fuentes de datos configuradas en el sistema.
-- ============================================
CREATE TABLE sources (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    base_url    TEXT NOT NULL,
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Tabla: companies
-- Empresas deduplicadas.
-- ============================================
CREATE TABLE companies (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Tabla: jobs
-- Ofertas de empleo. Unidad central del sistema.
-- ============================================
CREATE TABLE jobs (
    id              SERIAL PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    company_id      INTEGER REFERENCES companies(id),
    title           VARCHAR(255) NOT NULL,
    country         VARCHAR(100),
    published_at    DATE,
    url             TEXT NOT NULL UNIQUE,
    work_type       VARCHAR(20),
    description     TEXT,
    salary_raw      TEXT,
    seniority       VARCHAR(20),
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_published_at ON jobs(published_at);
CREATE INDEX idx_jobs_source_id ON jobs(source_id);
CREATE INDEX idx_jobs_seniority ON jobs(seniority);
CREATE INDEX idx_jobs_work_type ON jobs(work_type);

-- ============================================
-- Tabla: technologies
-- Catálogo de tecnologías conocidas.
-- ============================================
CREATE TABLE technologies (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    category    VARCHAR(50) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Tabla: job_technologies
-- Relación muchos-a-muchos entre ofertas y tecnologías.
-- ============================================
CREATE TABLE job_technologies (
    job_id          INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    technology_id   INTEGER NOT NULL REFERENCES technologies(id),
    PRIMARY KEY (job_id, technology_id)
);

CREATE INDEX idx_job_technologies_technology_id ON job_technologies(technology_id);

-- ============================================
-- Tabla: daily_snapshots
-- Métricas agregadas por día.
-- ============================================
CREATE TABLE daily_snapshots (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL UNIQUE,
    total_jobs      INTEGER NOT NULL,
    total_companies INTEGER NOT NULL,
    jobs_by_source  JSONB,
    jobs_by_seniority JSONB,
    jobs_by_work_type JSONB,
    top_technologies JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);