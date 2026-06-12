# JobFinding

Plataforma de inteligencia del mercado laboral tecnológico para LATAM.

## Requisitos

- Docker y Docker Compose
- Git

## Setup inicial

### 1. Clonar el repo

```bash
git clone <repo-url>
cd JobFinding
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con los valores deseados
```

### 3. Levantar la base de datos

```bash
docker compose up postgres -d
```

### 4. Verificar que PostgreSQL está corriendo

```bash
docker compose exec postgres psql -U jobfinding -c "\l"
```

Debería mostrar la base de datos `jobfinding`.

## Estructura del proyecto

```
jobfinding/
├── frontend/       # React + Vite + Tailwind (deploy a Vercel)
├── backend/        # FastAPI (deploy en servidor propio)
├── scraper/       # Python + BeautifulSoup (corre via cron)
├── database/       # Schemas y seeds de PostgreSQL
├── analytics/      # Scripts de agregación
├── docker/         # Dockerfiles
└── scripts/        # Utilidades
```

## Desarrollo

### Levantar todo (excepto scraper)

```bash
docker compose up -d postgres backend
```

### Correr el scraper manualmente

```bash
docker compose run --rm scraper python main.py
```

### Ver logs

```bash
docker compose logs -f backend
docker compose logs -f postgres
```

## Deployment

- **Frontend**: desplegado automáticamente en Vercel desde la carpeta `frontend/`
- **Backend + DB + Scraper**: en servidor propio via Docker Compose

## Licencia

MIT