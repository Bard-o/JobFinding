# AGENTS.md — JobFinding

Contexto global del proyecto. Lee este archivo al inicio de cada sesión antes de escribir cualquier código.

---

## Qué es este proyecto

JobFinding es una plataforma de inteligencia del mercado laboral tecnológico para LATAM.
Recopila ofertas de empleo diariamente, extrae tecnologías y niveles de seniority, almacena históricos y los presenta en un dashboard web.

**No es un portal de empleos. El valor está en las estadísticas y tendencias, no en las ofertas individuales.**

---

## Monorepo — Estructura de carpetas

```
jobfinding/
├── frontend/       # React + Vite + Tailwind + shadcn/ui + Apache ECharts
├── backend/        # FastAPI + SQLAlchemy + Pydantic
├── scraper/        # Python + Requests + BeautifulSoup
├── analytics/      # Scripts de agregación y procesamiento estadístico
├── database/       # Migraciones SQL, schema inicial, seeds
├── docker/         # Dockerfiles por servicio
├── docs/           # Documentación adicional
└── scripts/        # Utilidades: backup, reset DB, etc.
```

Cada carpeta es un módulo independiente. No crear dependencias cruzadas entre `scraper/` y `backend/` — ambos acceden a la DB directamente pero no se llaman entre sí.

---

## Stack por módulo

| Módulo | Tecnologías |
|---|---|
| Frontend | React 18, Vite, TypeScript, TailwindCSS, shadcn/ui, Apache ECharts |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, Uvicorn |
| Scraper | Python 3.11+, Requests, BeautifulSoup4 |
| Base de datos | PostgreSQL 15 |
| Infraestructura | Docker, Docker Compose |

---

## Convenciones de código

### Python (backend, scraper, analytics)
- Formato: Black, line length 88
- Imports: isort con perfil Black
- Type hints obligatorios en todas las funciones
- Nombres de variables y funciones: `snake_case`
- Nombres de clases: `PascalCase`
- Constantes: `UPPER_SNAKE_CASE`
- Strings: comillas dobles

### TypeScript / React (frontend)
- Componentes: `PascalCase`, un componente por archivo
- Hooks: prefijo `use`, `camelCase`
- Utilidades: `camelCase`
- Estilos: solo Tailwind, sin CSS modules ni styled-components
- No usar `any` — si el tipo es desconocido, definirlo explícitamente

### SQL / Base de datos
- Nombres de tablas: `snake_case`, plural (`jobs`, `companies`)
- Nombres de columnas: `snake_case`
- PKs: siempre `id SERIAL PRIMARY KEY`
- Timestamps: siempre `created_at TIMESTAMPTZ DEFAULT NOW()`
- FKs: nombrarlas explícitamente (`fk_job_technologies_job_id`)

---

## Variables de entorno

Nunca hardcodear credenciales ni URLs. Usar siempre variables de entorno.

Archivo de referencia: `.env.example` en la raíz del proyecto.

Variables mínimas requeridas:

```
# Base de datos
DATABASE_URL=postgresql://user:password@localhost:5432/jobfinding

# Telegram (alertas del scraper)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Reglas absolutas

- **No modificar archivos de migraciones ya aplicados.** Si hay un cambio de schema, crear una nueva migración.
- **No instalar dependencias no listadas en este documento sin documentarlas aquí.**
- **No usar `print()` para logging en producción.** Usar el módulo `logging` de Python o `structlog`.
- **No commitear archivos `.env`.** Solo `.env.example`.
- **El scraper no llama al backend.** Escribe directamente en la DB vía SQLAlchemy.
- **El frontend no accede a la DB directamente.** Solo consume la API del backend.

---

## Lo que NO está en el scope del MVP

No implementar ninguno de estos aunque parezca útil:

- Autenticación de usuarios
- Perfiles de usuario
- Alertas para usuarios finales
- Aplicación a empleos desde la plataforma
- Sistemas de pago
- Microservicios
- Machine Learning entrenado (NER, embeddings, etc.)
- Kubernetes

---

## Estado actual del proyecto

> **Actualizar esta sección al completar cada fase.**

- [x] Fase 1: Setup inicial (monorepo, Docker Compose, DB base)
- [x] Fase 2: Schema de base de datos
- [x] Fase 3: Scraper — GetOnBoard
- [x] Fase 4: ETL y procesamiento
- [ ] Fase 5: Data quality checks y alertas Telegram
- [ ] Fase 6: Generación de snapshots diarios
- [ ] Fase 7: Backend API
- [ ] Fase 8: Frontend dashboard
- [ ] Fase 9: Scraper — Remotive
- [ ] Fase 10: Export de datos
