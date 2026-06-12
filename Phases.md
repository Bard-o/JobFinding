# PHASES.md — JobFinding

Fases de construcción en orden. Completar cada fase en secuencia.
Al terminar cada fase: marcarla como completada en este archivo y en `AGENTS.md`.

**Criterio de verificación:** cada fase incluye una prueba concreta. Si la prueba pasa, la fase está completa.

---

## Fase 1 — Setup inicial ✅

**Objetivo:** monorepo funcional con Docker Compose levantando PostgreSQL.

**Tareas:****
- Crear estructura de carpetas del monorepo según `AGENTS.md`
- Crear `docker-compose.yml` con el servicio `postgres`
- Crear `.env.example` con las variables listadas en `AGENTS.md`
- Crear `database/init.sql` con extensiones básicas (`uuid-ossp`, `pg_trgm`)
- Crear `README.md` con instrucciones de setup

**Verificación:**
```bash
docker compose up postgres -d
docker compose exec postgres psql -U postgres -c "\l"
# Debe mostrar la base de datos 'jobfinding'
```

---

## Fase 2 — Schema de base de datos ✅

**Objetivo:** todas las tablas creadas con índices y seeds de tecnologías.

**Tareas:**
- Crear `database/schema.sql` con todas las tablas definidas en `ARCHITECTURE.md`
- Crear `database/seeds/technologies.sql` con el catálogo completo de tecnologías
- Crear `database/seeds/sources.sql` con GetOnBoard y Remotive
- Aplicar schema y seeds al contenedor de postgres

**Verificación:**
```bash
docker compose exec postgres psql -U jobfinding -d jobfinding -c "\dt"
# Debe listar: sources, companies, jobs, technologies, job_technologies, daily_snapshots

docker compose exec postgres psql -U jobfinding -d jobfinding -c "SELECT COUNT(*) FROM technologies;"
# Retorna 44 (catálogo expandido del documentado en ARCHITECTURE.md)
```

---

## Fase 3 — Scraper: GetOnBoard ✅

**Objetivo:** scraper funcional que extrae ofertas de GetOnBoard y las inserta en la DB.

**Tareas:**
- Crear `scraper/scrapers/getonboard.py` con clase `GetOnBoardScraper`
- Implementar paginación hasta agotar resultados
- Extraer campos: `title`, `company`, `country`, `published_at`, `url`, `work_type`, `description`
- Insertar en `jobs` con `ON CONFLICT (url) DO NOTHING`
- Crear `scraper/main.py` como punto de entrada
- Crear `docker/scraper.Dockerfile`

**Verificación:**
```bash
docker compose run --rm scraper python main.py --source getonboard --limit 10
# No debe lanzar excepciones
docker compose exec postgres psql -U postgres -d jobfinding -c "SELECT COUNT(*) FROM jobs;"
# Debe retornar > 0
docker compose exec postgres psql -U postgres -d jobfinding -c "SELECT title, url FROM jobs LIMIT 3;"
# Debe mostrar títulos y URLs reales de GetOnBoard
```

---

## Fase 4 — ETL y procesamiento ✅

**Objetivo:** pipeline que extrae tecnologías y seniority de las descripciones ya almacenadas.

**Tareas:**
- [x] Crear `scraper/extractors/tech_extractor.py` con lógica de matching por diccionario (regex `\b{tech}\b`)
- [x] Crear `scraper/extractors/seniority_extractor.py` con keywords definidas en `ARCHITECTURE.md`
- [x] Poblar `job_technologies` para los jobs ya insertados
- [x] Actualizar columna `seniority` en `jobs`
- [x] Crear `scraper/etl/pipeline.py` que orqueste extracción → inserción

**Verificación:**
```bash
docker compose run --rm scraper python -c "from etl.pipeline import run_pipeline; run_pipeline()"
docker compose exec postgres psql -U postgres -d jobfinding -c "
SELECT t.name, COUNT(*) as apariciones
FROM job_technologies jt
JOIN technologies t ON jt.technology_id = t.id
GROUP BY t.name ORDER BY apariciones DESC LIMIT 5;"
# Debe mostrar las 5 tecnologías más frecuentes con conteos reales

docker compose exec postgres psql -U postgres -d jobfinding -c "
SELECT seniority, COUNT(*) FROM jobs GROUP BY seniority;"
# Debe mostrar distribución con algunos NULLs (normal)
```

---

## Fase 5 — Data quality checks y alertas Telegram

**Objetivo:** el pipeline detecta anomalías y notifica por Telegram.

**Tareas:**
- Crear `scraper/alerts/telegram.py` con función `send_alert(message)`
- Crear `scraper/quality/checks.py` con los 4 checks definidos en `ARCHITECTURE.md`
- Integrar checks al final de `etl/pipeline.py`
- Leer `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` desde variables de entorno

**Verificación:**
```bash
# Simular fallo forzando un check con datos artificiales
docker compose run --rm scraper python -c "
from quality.checks import run_checks
run_checks(jobs_today=5, avg_7d=200, empty_descriptions=0, total=5, sources_with_data=['getonboard'])
"
# Debe enviar un mensaje de alerta al chat de Telegram configurado
# Verificar que el mensaje llegue al teléfono
```

---

## Fase 6 — Generación de snapshots diarios

**Objetivo:** al finalizar cada ejecución, se genera un registro en `daily_snapshots`.

**Tareas:**
- Crear `analytics/snapshot_generator.py` con lógica de agregación
- Calcular: `total_jobs`, `total_companies`, `jobs_by_source`, `jobs_by_seniority`, `jobs_by_work_type`, `top_technologies` (top 20)
- Insertar en `daily_snapshots` con `ON CONFLICT (snapshot_date) DO UPDATE`
- Llamar al generador al final del pipeline principal

**Verificación:**
```bash
docker compose run --rm scraper python -c "from analytics.snapshot_generator import generate; generate()"
docker compose exec postgres psql -U postgres -d jobfinding -c "
SELECT snapshot_date, total_jobs, top_technologies FROM daily_snapshots ORDER BY snapshot_date DESC LIMIT 1;"
# Debe mostrar un registro con fecha de hoy y JSON de tecnologías
```

---

## Fase 7 — Backend API

**Objetivo:** FastAPI sirviendo todos los endpoints definidos en `ARCHITECTURE.md`.

**Tareas:**
- Crear `backend/main.py` con app FastAPI
- Crear `backend/database.py` con configuración de SQLAlchemy
- Crear `backend/models/` con modelos ORM para cada tabla
- Crear `backend/routers/` con un archivo por grupo de endpoints (`summary`, `technologies`, `jobs`, `export`)
- Crear `backend/schemas/` con schemas Pydantic para responses
- Crear `docker/backend.Dockerfile`
- Configurar CORS para permitir el frontend en desarrollo

**Verificación:**
```bash
docker compose up backend -d
curl http://localhost:8000/api/v1/health
# {"status": "ok"}

curl http://localhost:8000/api/v1/summary
# JSON con campos: total_jobs, total_companies, top_technologies, etc.

curl "http://localhost:8000/api/v1/jobs?page=1&page_size=5"
# JSON con lista de ofertas paginada

curl http://localhost:8000/api/v1/technologies
# JSON con lista de tecnologías y conteos
```

---

## Fase 8 — Frontend dashboard

**Objetivo:** dashboard funcional consumiendo la API, con charts de tecnologías, seniority y tendencias.

**Tareas:**
- Crear proyecto Vite + React + TypeScript en `frontend/`
- Configurar TailwindCSS y shadcn/ui
- Crear componentes:
  - `SummaryCards` — total ofertas, empresas, tecnologías
  - `TopTechnologiesChart` — bar chart con top 10 tecnologías (ECharts)
  - `SeniorityPieChart` — distribución de seniority (ECharts)
  - `WorkTypeChart` — remoto / híbrido / presencial (ECharts)
  - `TrendsChart` — evolución temporal de tecnologías seleccionadas (ECharts)
  - `JobsTable` — tabla con filtros: tecnología, seniority, work_type
- Configurar `VITE_API_URL` desde `.env`
- Crear `docker/frontend.Dockerfile` con build de producción

**Verificación:**
```bash
docker compose up frontend -d
# Abrir http://localhost:3000 en el browser
# Checklist visual:
# [ ] Los 3 summary cards muestran números reales (no 0 ni undefined)
# [ ] El bar chart de tecnologías tiene al menos 5 barras con nombres reales
# [ ] El pie chart de seniority tiene sectores visibles
# [ ] La tabla de jobs carga al menos una fila
# [ ] El filtro de tecnología filtra la tabla correctamente
```

---

## Fase 9 — Scraper: Remotive

**Objetivo:** segunda fuente de datos integrada al pipeline.

**Tareas:**
- Crear `scraper/scrapers/remotive.py` con clase `RemotiveScraper`
- Remotive tiene API pública JSON en `https://remotive.com/api/remote-jobs` — usar esa en lugar de HTML scraping
- Normalizar campos al mismo formato que GetOnBoard
- Integrar al pipeline principal
- Actualizar `scraper/main.py` para correr ambas fuentes en secuencia

**Verificación:**
```bash
docker compose run --rm scraper python main.py --source remotive --limit 10
docker compose exec postgres psql -U postgres -d jobfinding -c "
SELECT source_id, COUNT(*) FROM jobs GROUP BY source_id;"
# Debe mostrar conteos para ambas fuentes (source_id 1 y 2)
```

---

## Fase 10 — Export de datos

**Objetivo:** endpoints de export generan archivos descargables.

**Tareas:**
- Implementar `GET /api/v1/export/csv` usando `csv` de stdlib Python
- Implementar `GET /api/v1/export/excel` usando `openpyxl`
- Ambos endpoints aceptan los mismos filtros que `/jobs`
- Response con headers correctos (`Content-Disposition: attachment`)

**Verificación:**
```bash
curl -o jobs_export.csv "http://localhost:8000/api/v1/export/csv"
# Abrir el archivo — debe tener headers y filas con datos reales

curl -o jobs_export.xlsx "http://localhost:8000/api/v1/export/excel"
# Abrir en Excel/LibreOffice — debe abrir sin errores y mostrar datos
```

---

## Notas para fases futuras (fuera del MVP)

- **Deduplicación cross-source:** comparar `title + company_id + published_at` con ventana ±1 día
- **Dominio propio + Cloudflare Tunnel:** cuando el proyecto esté listo para portafolio público
- **Fuentes adicionales:** RemoteOK, Hacker News Jobs, canales de Telegram
- **LLMs para extracción:** reemplazar el extractor de keywords por un modelo local cuando el volumen justifique la mejora
