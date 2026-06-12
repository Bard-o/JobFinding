# ARCHITECTURE.md — JobFinding

Decisiones técnicas fijas del sistema. No cambiar sin actualizar este documento primero.

---

## Flujo general del sistema

```
[Cron del host] → docker compose run --rm scraper
                        ↓
              Scraping (Requests + BS4)
                        ↓
              ETL / Procesamiento
              - Normalización
              - Extracción de tecnologías (diccionario)
              - Extracción de seniority (keywords)
              - Deduplicación por URL
              - Data quality checks
                        ↓
              PostgreSQL (escritura directa vía SQLAlchemy)
                        ↓
              [FastAPI expone los datos]
                        ↓
              [React + Vite consume la API]
```

---

## Base de datos — Schema

### Tabla: `sources`
Fuentes de datos configuradas en el sistema.

```sql
CREATE TABLE sources (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,  -- 'getonboard', 'remotive'
    base_url    TEXT NOT NULL,
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: `companies`
Empresas deduplicadas.

```sql
CREATE TABLE companies (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: `jobs`
Ofertas de empleo. Unidad central del sistema.

```sql
CREATE TABLE jobs (
    id              SERIAL PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    company_id      INTEGER REFERENCES companies(id),
    title           VARCHAR(255) NOT NULL,
    country         VARCHAR(100),
    published_at    DATE,
    url             TEXT NOT NULL UNIQUE,        -- constraint de deduplicación intra-source
    work_type       VARCHAR(20),                 -- 'remote', 'hybrid', 'onsite'
    description     TEXT,
    salary_raw      TEXT,                        -- guardar raw, no parsear en MVP
    seniority       VARCHAR(20),                 -- 'junior', 'mid', 'senior', 'lead', NULL
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_published_at ON jobs(published_at);
CREATE INDEX idx_jobs_source_id ON jobs(source_id);
CREATE INDEX idx_jobs_seniority ON jobs(seniority);
CREATE INDEX idx_jobs_work_type ON jobs(work_type);
```

### Tabla: `technologies`
Catálogo de tecnologías conocidas.

```sql
CREATE TABLE technologies (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,    -- 'React', 'Python', 'Docker'
    category    VARCHAR(50) NOT NULL,            -- 'language', 'framework', 'cloud', 'devops', 'database'
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: `job_technologies`
Relación muchos-a-muchos entre ofertas y tecnologías.

```sql
CREATE TABLE job_technologies (
    job_id          INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    technology_id   INTEGER NOT NULL REFERENCES technologies(id),
    PRIMARY KEY (job_id, technology_id)
);

CREATE INDEX idx_job_technologies_technology_id ON job_technologies(technology_id);
```

### Tabla: `daily_snapshots`
Métricas agregadas por día. Se genera al finalizar cada ejecución del scraper.

```sql
CREATE TABLE daily_snapshots (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL UNIQUE,
    total_jobs      INTEGER NOT NULL,
    total_companies INTEGER NOT NULL,
    jobs_by_source  JSONB,      -- {"getonboard": 120, "remotive": 80}
    jobs_by_seniority JSONB,    -- {"junior": 40, "mid": 90, "senior": 60, "lead": 10}
    jobs_by_work_type JSONB,    -- {"remote": 130, "hybrid": 50, "onsite": 20}
    top_technologies JSONB,     -- [{"name": "Python", "count": 95}, ...]
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Estrategia de deduplicación

**Intra-source:** constraint `UNIQUE` en `jobs.url`. El ETL hace upsert — si el URL ya existe, ignora el registro sin error.

```python
# Patrón de inserción en el ETL
INSERT INTO jobs (...) VALUES (...)
ON CONFLICT (url) DO NOTHING;
```

**Cross-source:** no implementado en MVP. Nota para fase futura: comparar `title + company_id + published_at` con ventana de tolerancia de ±1 día.

---

## Extracción de tecnologías

Detección por diccionario. Búsqueda case-insensitive sobre `jobs.description`.

Diccionario seed en `database/seeds/technologies.sql`. Formato:

```
name         | category
-------------|----------
Python       | language
JavaScript   | language
TypeScript   | language
Go           | language
Rust         | language
Java         | language
C#           | language
React        | framework
Angular      | framework
Vue          | framework
Django       | framework
FastAPI      | framework
Spring       | framework
AWS          | cloud
Azure        | cloud
GCP          | cloud
Docker       | devops
Kubernetes   | devops
Terraform    | devops
PostgreSQL   | database
MySQL        | database
MongoDB      | database
Redis        | database
```

Lógica de matching en `scraper/extractors/tech_extractor.py`. Usar `re.search(r'\b{tech}\b', description, re.IGNORECASE)` para evitar falsos positivos (ej. "Java" dentro de "JavaScript").

---

## Extracción de seniority

Keywords por nivel, evaluadas en orden de prioridad (lead > senior > mid > junior).

```python
SENIORITY_KEYWORDS = {
    "lead":   ["lead", "staff", "principal", "head of", "tech lead"],
    "senior": ["senior", "sr.", "sr "],
    "mid":    ["mid", "middle", "semi-senior", "ssr", "semi senior"],
    "junior": ["junior", "jr.", "jr ", "entry level", "entry-level", "trainee"],
}
```

Si no hay match → `seniority = NULL`.

---

## Data quality checks

Ejecutar al final del ETL, antes de generar el snapshot diario.

| Check | Condición de alerta |
|---|---|
| Volumen total | Ofertas del día < 50% del promedio de los últimos 7 días |
| Descripciones vacías | Más del 30% de ofertas con `description` menor a 50 caracteres |
| Fuente sin datos | Cualquier fuente activa con 0 ofertas nuevas en la ejecución |
| Tecnologías no detectadas | Más del 60% de ofertas sin ninguna tecnología asociada |

El umbral de descripción es **50 caracteres** — suficiente para detectar campos vacíos o placeholders, sin descartar descripciones legítimamente cortas.

Si algún check falla → enviar alerta por Telegram y continuar (fail silently).

---

## Alertas — Telegram

Módulo en `scraper/alerts/telegram.py`.

```python
def send_alert(message: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, json=payload, timeout=10)
```

Formato del mensaje de alerta:

```
⚠️ JobFinding — Data Quality Alert
Fecha: 2024-01-15
Checks fallidos:
- Volumen bajo: 45 ofertas (promedio 7d: 180)
- Fuente sin datos: remotive
```

---

## Estrategia de renderizado del frontend

| Tipo de contenido | Estrategia |
|---|---|
| Dashboard principal (stats globales, charts de tendencias) | ISR — revalidate cada 86400 segundos (24h) |
| Filtros interactivos del usuario | CSR — fetch al API en runtime |
| Páginas estáticas (about, docs) | SSG puro |

**Nota:** dado que se usa React + Vite (no Next.js), ISR no está disponible nativamente. La estrategia equivalente es:
- El backend expone un endpoint `/api/summary` que devuelve el snapshot más reciente de `daily_snapshots`.
- El frontend hace fetch de ese endpoint al cargar la página (CSR).
- El snapshot se actualiza una vez al día cuando corre el scraper.
- Para filtros: endpoints separados con parámetros de query (`/api/jobs?tech=React&seniority=senior`).

---

## Scheduler

El scraper **no corre como servicio permanente**. Es un job que nace, ejecuta y muere.

```bash
# Entrada en crontab del host (ejemplo: 2:00 AM UTC todos los días)
0 2 * * * cd /path/to/jobfinding && docker compose run --rm scraper >> /var/log/jobfinding-scraper.log 2>&1
```

Servicios permanentes en Docker Compose: `postgres`, `backend`, `frontend`.
El servicio `scraper` solo existe como definición para correrlo con `run --rm`.

---

## API — Endpoints del backend

Base URL: `http://localhost:8000/api/v1`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/summary` | Snapshot más reciente de `daily_snapshots` |
| GET | `/technologies` | Lista de tecnologías con conteo de apariciones |
| GET | `/technologies/trends` | Evolución temporal por tecnología (param: `?days=30`) |
| GET | `/jobs` | Listado paginado de ofertas (filtros: `tech`, `seniority`, `work_type`, `country`) |
| GET | `/jobs/{id}` | Detalle de una oferta |
| GET | `/seniority/distribution` | Distribución de seniority |
| GET | `/export/csv` | Export de ofertas a CSV |
| GET | `/export/excel` | Export de ofertas a Excel |
| GET | `/health` | Health check del servicio |

Paginación estándar: `?page=1&page_size=20`. Máximo `page_size`: 100.

---

## Docker Compose — Servicios

```yaml
services:
  postgres:
    image: postgres:15
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql

  backend:
    build: ./docker/backend.Dockerfile
    restart: always
    depends_on: [postgres]
    ports:
      - "8000:8000"

  frontend:
    build: ./docker/frontend.Dockerfile
    restart: always
    ports:
      - "3000:3000"

  scraper:
    build: ./docker/scraper.Dockerfile
    profiles: ["job"]       # solo se levanta con docker compose run
    depends_on: [postgres]

volumes:
  postgres_data:
```
