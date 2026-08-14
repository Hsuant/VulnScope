<div align="center">
  <h1>VulnScope</h1>
  <p><strong>POC (Proof of Concept) Vulnerability Script Management System</strong></p>
  <p>Manage, store, search, import, and export POC assets with tagging, CVE association, and RBAC</p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.4%2B-4FC08D?logo=vue.js" alt="Vue 3">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-333333?logo=sqlalchemy" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## Features

- **Full POC Lifecycle** — Create, edit, version history, clone, status transitions
- **Multi-format Support** — Nuclei YAML, Pocsuite3, JSON, raw scripts; format-agnostic architecture
- **Batch Import/Export** — Auto format detection, content deduplication, multi-file support
- **Tag & Category System** — Namespace-based tags + tree categories for flexible POC organization
- **CVE Vulnerability Database** — Auto CVE association, bidirectional search between vulns and POCs
- **Dashboard & Analytics** — Severity/status/source distribution, creation trends, top tags, top authors
- **RBAC** — Three roles (viewer / editor / admin), granular access control
- **Audit Logging** — Full write operation trail with before/after summaries and IP recording
- **Plugin Framework** — Four slots: Parser, Source, Verifier, Exporter; plug-and-play
- **Event-driven Architecture** — Async domain event dispatch, decoupled module integration

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Optional: MySQL 8.0 (production)

### Backend

```bash
# Enter backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Install dependencies (including dev)
.venv/Scripts/pip install -e ".[dev]"

# Copy environment config
cp .env.example .env

# Run database migrations
.venv/Scripts/alembic upgrade head

# Start development server (with auto-reload)
.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
# Enter frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Docker Deployment (Optional)

A `docker-compose.yml` is included for one-command startup of both frontend and backend:

```bash
# From the project root
docker compose up -d
```

### Access URLs

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Frontend admin panel |
| http://localhost:8000/docs | Swagger UI interactive docs |
| http://localhost:8000/api/v1/health | Health check |

### Default Admin Account

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | admin |

## Project Structure

```
VulnScope/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── main.py           # App entry + lifecycle
│   │   ├── core/             # Config / exceptions / security / events / cache
│   │   ├── db/               # Session management / base classes
│   │   ├── models/           # ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── api/v1/           # REST API routes
│   │   ├── services/         # Business logic layer
│   │   └── plugins/          # Plugin framework
│   ├── tests/                # pytest test suite
│   ├── alembic/              # Database migrations
│   ├── Dockerfile            # Backend image
│   ├── start.bat / start.sh  # Startup scripts
│   └── pyproject.toml        # Dependencies + tooling config
├── frontend/                 # Vue 3 frontend
│   └── src/
│       ├── views/            # Page components
│       ├── components/       # Shared components
│       ├── composables/      # Composition functions
│       ├── api/              # API client
│       ├── stores/           # State management
│       ├── router/           # Routing
│       └── styles/           # Global styles
├── docs/                     # Documentation + usage guide
└── docker-compose.yml        # One-command Docker deployment
```

## API Overview

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/auth/login` | Login | None |
| POST | `/api/v1/auth/refresh` | Refresh token | None |
| GET | `/api/v1/auth/me` | Current user | Required |
| PUT | `/api/v1/auth/profile` | Update own profile | Required |
| GET/POST | `/api/v1/pocs` | List/Create POCs | Required |
| GET | `/api/v1/pocs/search` | Keyword search | Required |
| GET/PUT/DELETE | `/api/v1/pocs/{id}` | POC detail/update/delete | Required |
| PATCH | `/api/v1/pocs/{id}/status` | Status transition | editor/admin |
| POST | `/api/v1/pocs/{id}/clone` | Clone POC | editor/admin |
| GET | `/api/v1/pocs/{id}/versions` | Version history | Required |
| GET | `/api/v1/pocs/{id}/source-records` | Source provenance | Required |
| POST | `/api/v1/pocs/verify-url` | Verify URL | Required |
| POST | `/api/v1/import` | Import POCs | editor/admin |
| GET | `/api/v1/export` | Export POCs | Required |
| GET/POST/PUT/DELETE | `/api/v1/tags` | Tag management | Required |
| GET | `/api/v1/tags/namespaces` | Tag namespaces | Required |
| GET | `/api/v1/vulns` | CVE database | Required |
| GET | `/api/v1/vulns/by-cve/{cve_id}` | Lookup by CVE ID | Required |
| GET | `/api/v1/dashboard/*` | Dashboard stats | Required |
| GET/POST/PUT/DELETE | `/api/v1/users` | User management | admin |
| GET | `/api/v1/users/roles` | Role list | admin |
| GET | `/api/v1/plugins` | Plugin list | Required |
| GET | `/api/v1/plugins/{slot}` | Plugins by slot | Required |
| GET | `/api/v1/audit-logs` | Audit logs | admin |

## Configuration

Configure via environment variables or `.env` file. All variables use the `VULNSCOPE_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `VULNSCOPE_APP_ENV` | `dev` | Runtime environment (dev / test / prod) |
| `VULNSCOPE_DB_BACKEND` | `sqlite` | Database backend (sqlite / mysql) |
| `VULNSCOPE_DATABASE_URL` | generated | Explicit DB URL (takes precedence) |
| `VULNSCOPE_CACHE_BACKEND` | `inproc` | Cache backend (inproc / redis, v2) |
| `VULNSCOPE_SECRET_KEY` | dev key | JWT signing key — change in production |
| `VULNSCOPE_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token TTL |
| `VULNSCOPE_REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token TTL |
| `VULNSCOPE_SEED_ADMIN_USERNAME` | `admin` | Seed admin username |
| `VULNSCOPE_SEED_ADMIN_PASSWORD` | `admin123` | Seed admin password |

> The full set of options is defined in `backend/app/core/config.py`; every variable uses the `VULNSCOPE_` prefix.

## Running Tests

```bash
cd backend
.venv/Scripts/pytest -v                    # Run all tests
.venv/Scripts/pytest --cov=app tests/       # With coverage
```

## Tech Stack

| Layer | Component | Purpose |
|-------|-----------|---------|
| Framework | FastAPI + Uvicorn | Async routing, auto OpenAPI docs |
| ORM | SQLAlchemy 2.0 + Alembic | Declarative models, versioned migrations |
| Validation | Pydantic v2 | Request/response models, config validation |
| Auth | bcrypt + PyJWT | Password hashing, dual-token auth |
| Cache | cachetools | In-process TTL cache |
| Frontend | Vue 3 + TypeScript | Composition API |
| UI | Element Plus | Component library |
| Build | Vite | Frontend build tool |

## Detailed Usage Guide

📖 For a complete walkthrough, see the [Usage Guide](docs/usage-guide.md) (Chinese). It covers:

- **Creating a POC** — Basic info, associations, form builder (HTTP/TCP/DNS protocols), matcher rules, source mode
- **Tag Management** — Namespace system, create/edit/delete tags, best practices
- **Import/Export** — Batch file upload, paste text, auto format detection
- **FAQ** — Name conflicts, format limitations, version rollback, content deduplication

## Development Milestones

- ✅ **M1 Skeleton** — Project scaffolding, config, auth, exceptions, plugin interfaces
- ✅ **M2 Core Storage** — POC CRUD, tags/categories, CVE association, search
- ✅ **M3 Plugin Framework** — Registry, event bus, Parser/Source slots
- ✅ **M4 Import/Export** — Import wizard, format detection, dedup, export
- ✅ **M5 Frontend** — Complete admin UI
- ✅ **M6 Deployment** — One-command Docker Compose
- ⏳ **M7 Polish** — Benchmarking, performance optimization
- ⏳ **v2 Verification** — Remote POC execution
- ⏳ **v2 AI Generation** — POC auto-generation from vulnerability descriptions
- ⏳ **v2 Crawler** — Automated POC crawling

## License

MIT