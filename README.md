# Weather Middleware Platform

A production-grade weather data ingestion and processing system built with two independent FastAPI microservices, PostgreSQL, async SQLAlchemy 2, and Docker Compose. Designed following Clean Architecture principles, the Repository Pattern, and the 12-Factor App methodology.

> **Goal:** demonstrate real-world backend engineering — from architecture design and domain modeling to REST API design, persistence, testing, and infrastructure-as-code planning.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Services](#services)
  - [Ingestion Service](#ingestion-service)
  - [Processing Service](#processing-service)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
  - [A Note on Organizational Patterns](#a-note-on-organizational-patterns)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Running with Docker Compose](#running-with-docker-compose)
  - [Running Locally (without Docker)](#running-locally-without-docker)
  - [AI Agent Skills (Library Skills)](#ai-agent-skills-library-skills)
- [API Reference](#api-reference)
  - [Ingestion Service API](#ingestion-service-api)
  - [Processing Service API](#processing-service-api)
  - [Authentication](#authentication)
- [Data Model](#data-model)
- [Testing](#testing)
- [Design Decisions (ADRs)](#design-decisions-adrs)
- [Planned Infrastructure (AWS)](#planned-infrastructure-aws)
- [Future Improvements](#future-improvements)

---

## Overview

This platform simulates a lab instrument middleware system applied to weather data. It continuously fetches weather readings from [Open-Meteo](https://open-meteo.com/) (a free, no-auth weather API), stores the raw observations, and then processes them to compute derived meteorological metrics, evaluate configurable business rules, and generate alerts when thresholds are breached.

```
Open-Meteo API
      │
      ▼
┌─────────────────────┐         ┌──────────────────────────┐
│  Ingestion Service  │ ──REST──▶  Processing Service       │
│  (port 8000)        │         │  (port 8001)              │
│                     │         │                           │
│  • Stores locations │         │  • Fetches raw data       │
│  • Polls Open-Meteo │         │  • Computes metrics       │
│  • Saves raw data   │         │  • Evaluates rules        │
└─────────────────────┘         │  • Generates alerts       │
         │                      └──────────────────────────┘
         │                                 │
         └──────────┬──────────────────────┘
                    ▼
             PostgreSQL 16
         ┌──────────────────┐
         │ schema: ingestion │
         │ schema: processing│
         └──────────────────┘
```

**Key behaviors:**

- Ingestion service polls Open-Meteo every **15 minutes** for all active locations.
- Processing service runs every **5 minutes**, picking up new raw observations via a high-water mark watermark strategy.
- Both cycles can also be triggered **manually via REST** for testing.
- Raw observations are **immutable** — they are never modified after ingestion.
- Processing is **idempotent** — re-running never creates duplicate records.

---

## Architecture

The codebase follows **Clean Architecture** strictly. Each service is organized into four concentric layers:

```
┌────────────────────────────────────────────────┐
│                  Interface Layer               │  FastAPI routers, dependency injection
├────────────────────────────────────────────────┤
│               Application Layer                │  Use cases (orchestration only)
├────────────────────────────────────────────────┤
│                  Domain Layer                  │  Entities, repository protocols, ports
├────────────────────────────────────────────────┤
│              Infrastructure Layer              │  SQLAlchemy, asyncpg, HTTP clients, settings
└────────────────────────────────────────────────┘
```

**Dependency rule:** inner layers never import from outer layers. The domain knows nothing about SQLAlchemy, FastAPI, or HTTP — only pure Python dataclasses and `Protocol` interfaces.

**Key patterns applied:**

- **Repository Pattern** — domain defines `Protocol` contracts; SQLAlchemy implementations live in infrastructure. Swapping databases requires zero domain changes.
- **Adapter Pattern** — `OpenMeteoAdapter` implements the `WeatherDataSource` port, decoupling the domain from the external API provider.
- **Dependency Injection** — FastAPI's `Depends()` wires repositories and use cases at request time, without a DI container.
- **In-memory fakes for testing** — unit tests use `FakeLocationRepository` and `FakeWeatherDataSource` — no database, no mocks, no patching.

---

## Services

### Ingestion Service

Responsible for managing locations and collecting raw weather data.

**Responsibilities:**

- CRUD operations for monitored locations (lat/lon, timezone, active flag)
- Periodic polling of Open-Meteo for each active location (background asyncio task)
- Storing raw, immutable observations in the `ingestion` schema
- Exposing REST endpoints for manual ingestion and observation queries

**Background scheduler:** an asyncio loop started at application lifespan runs `IngestObservationsUseCase` every `INGESTION_INTERVAL_SECONDS` (default: 900). The use case fetches only active locations, calls the weather adapter, and bulk-saves results — silently deduplicating via `UNIQUE(location_id, observed_at)`.

### Processing Service

Responsible for turning raw weather data into actionable insights.

**Responsibilities:**

- Fetching unprocessed raw observations from the ingestion service via HTTP (paginated)
- Computing derived metrics: **heat index**, **wind chill**, and **feels-like temperature**
- Evaluating configurable **processing rules** (threshold-based, data-driven)
- Generating **alerts** with severity levels (LOW / MEDIUM / HIGH / CRITICAL)
- Tracking progress with a **high-water mark watermark** to ensure exactly-once processing
- Exposing REST endpoints for rules CRUD, processed data queries, and alert management

**Anti-join strategy:** the watermark records the timestamp of the last processed observation. On each cycle, the processing service requests only observations newer than this mark (`since` query param), and uses a `UNIQUE(raw_observation_id)` constraint on `processed_observations` as a final idempotency guard.

---

## Technology Stack

| Layer            | Technology              | Rationale                                            |
| ---------------- | ----------------------- | ---------------------------------------------------- |
| API Framework    | FastAPI                 | Async-native, automatic OpenAPI docs, first-class DI |
| ORM              | SQLAlchemy 2 (async)    | Mature, async support, explicit query control        |
| Driver           | asyncpg                 | Fastest PostgreSQL async driver for Python           |
| Database         | PostgreSQL 16           | ACID, rich constraint support, schema isolation      |
| Migrations       | Alembic                 | Version-controlled schema changes                    |
| HTTP Client      | httpx                   | Async HTTP for inter-service communication           |
| Config           | pydantic-settings       | Type-safe, env-var-driven configuration              |
| Testing          | pytest + pytest-asyncio | Async test support; in-memory fakes strategy         |
| Containerization | Docker + Docker Compose | Single-command local stack                           |
| Weather Data     | Open-Meteo              | Free, no API key, production-grade reliability       |
| IaC (planned)    | AWS CDK (TypeScript)    | Reproducible cloud infrastructure                    |

---

## Project Structure

```
WeatherAPI/
├── docker-compose.yml
├── .env.example
├── scripts/
│   └── init-db.sql              # Creates ingestion + processing schemas
├── docs/
│   ├── adr/                     # 11 Architecture Decision Records
│   ├── architecture/
│   │   ├── overview.md          # Full system architecture document
│   │   └── review-report.md    # Architecture review findings
│   └── WeatherAPI_Demo.postman_collection.json
├── ingestion-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                 # DB migrations
│   ├── src/
│   │   ├── domain/
│   │   │   ├── entities/        # Location, RawObservation (pure dataclasses)
│   │   │   ├── ports/           # WeatherDataSource Protocol
│   │   │   └── repositories/   # LocationRepository, RawObservationRepository Protocols
│   │   ├── application/
│   │   │   ├── dtos/            # LocationDTO, ObservationDTO
│   │   │   └── use_cases/      # RegisterLocation, IngestObservations, ListObservations, ...
│   │   ├── infrastructure/
│   │   │   ├── config/          # pydantic-settings
│   │   │   ├── external/        # OpenMeteoAdapter
│   │   │   └── persistence/    # SQLAlchemy models + repository implementations
│   │   └── interface/
│   │       ├── api/             # FastAPI routers (locations, observations, health)
│   │       ├── dependencies.py  # DI wiring
│   │       └── main.py          # App factory + lifespan scheduler
│   └── tests/unit/
│       ├── fakes.py             # In-memory repository fakes
│       └── test_*.py            # 18 unit tests
└── processing-service/
    ├── Dockerfile
    ├── requirements.txt
    ├── alembic/
    ├── src/
    │   ├── domain/
    │   │   ├── entities/        # ProcessedObservation, Alert, ProcessingRule, Watermark
    │   │   ├── ports/           # IngestionClient Protocol
    │   │   ├── repositories/   # 4 repository Protocols
    │   │   └── services/       # RuleEngine, MetricsCalculator (pure domain logic)
    │   ├── application/
    │   │   ├── dtos/            # ProcessedObservationDTO, AlertDTO, RuleDTO
    │   │   └── use_cases/      # ProcessObservations, CrudRules, ListAlerts, AcknowledgeAlert
    │   ├── infrastructure/
    │   │   ├── config/
    │   │   ├── external/        # HttpIngestionClient
    │   │   └── persistence/
    │   └── interface/
    │       ├── api/             # Routers for processed obs, alerts, rules, health
    │       ├── dependencies.py
    │       └── main.py
    └── tests/unit/
        ├── fakes.py
        └── test_*.py            # Unit tests for processing logic
```

### A Note on Organizational Patterns

For an API this small — a handful of entities per service — a plain **package by layer** structure (grouping files by technical type: `api/routes/`, `models.py`, `crud.py`, `core/`), the pattern used by the official [`full-stack-fastapi-template`](https://github.com/fastapi/full-stack-fastapi-template), would have been more than sufficient.

Instead, each service follows **Clean Architecture** (`domain/ → application/ → infrastructure/ → interface/`), with every layer split into one file per concept (`entities/location.py`, `entities/raw_observation.py`, `repositories/location_repository.py`, ...) instead of shared `models.py` / `crud.py` catch-alls. Combined with a top level split into two independently deployable, domain-named services (`ingestion-service/`, `processing-service/` — rather than technical folders like `api/` or `core/`), the result leans closer to a [**package by feature**](https://github.com/zhanymkanov/fastapi-best-practices) organization, where the folder tree "screams" the business domain rather than the framework used to build it.

This was a deliberate choice, not a necessity: the intent was to showcase how flexible FastAPI is regardless of the folder convention adopted, and to structure the codebase as if it already had to support many more domains — so that adding a new one (e.g. `forecasts/`, `alerting-channels/`) means dropping in a new self-contained module, not touching a shared `models.py` — even though, at the project's current size, the simpler pattern would have worked just as well.

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- (Optional, for local dev) Python 3.12+

### Running with Docker Compose

```bash
# 1. Clone the repository
git clone <repo-url>
cd WeatherAPI

# 2. Copy environment variables
cp .env.example .env

# 3. Start the full stack (Postgres + both services)
docker compose up --build
```

This will:

1. Start a PostgreSQL 16 container
2. Create the `ingestion` and `processing` schemas
3. Run Alembic migrations for both services
4. Start both FastAPI services

**Services will be available at:**

| Service            | URL                   | Interactive Docs           |
| ------------------ | --------------------- | -------------------------- |
| Ingestion Service  | http://localhost:8000 | http://localhost:8000/docs |
| Processing Service | http://localhost:8001 | http://localhost:8001/docs |
| Health checks      | `/health` on each     | —                          |

### Running Migrations Manually

```bash
# Ingestion service migrations
docker compose exec ingestion-service alembic upgrade head

# Processing service migrations
docker compose exec processing-service alembic upgrade head
```

### Running Locally (without Docker)

```bash
# Terminal 1 — Postgres (still needs Docker)
docker compose up postgres

# Terminal 2 — Ingestion Service
cd ingestion-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.interface.main:app --port 8000 --reload

# Terminal 3 — Processing Service
cd processing-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.interface.main:app --port 8001 --reload
```

### AI Agent Skills (Library Skills)

This repo uses [Library Skills](https://library-skills.io/) to keep AI coding agents (Cursor, Claude, etc.) up to date on how to use the libraries this project depends on (e.g. FastAPI). Skills are symlinked into `.agents/skills/` inside each service, pointing at docs bundled with the installed package in its `.venv`.

Because each service manages its own virtual environment, **run `library-skills` from inside each service directory**, after installing dependencies:

```bash
# Ingestion service
cd ingestion-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvx library-skills --all --yes

# Processing service
cd ../processing-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvx library-skills --all --yes
```

- `--all` selects every newly discovered skill; `--yes` skips the interactive prompts (required when running non-interactively, e.g. in scripts or automation).
- Since `.venv/` is gitignored, the committed `.agents/skills/*` symlinks will appear broken until you install dependencies locally — running the commands above will resolve them.
- To check whether skills are installed and up to date without changing anything, run `uvx library-skills --check` from within a service directory.
- Running plain `uvx library-skills` (no flags) from a service directory opens an interactive menu to select specific skills instead.

### Demo with Postman

Import `docs/WeatherAPI_Demo.postman_collection.json` into Postman. The collection includes a full scripted demo flow:

1. Health checks
2. Create locations (Medellín, Bogotá, Cartagena)
3. Trigger manual ingest + verify idempotency
4. Create processing rules (temperature thresholds, humidity, wind)
5. Trigger manual processing cycle
6. List processed observations and alerts
7. Acknowledge an alert

---

## API Reference

### Authentication

Write endpoints are protected with an API key passed in the header:

```
X-API-Key: local-dev-key
```

Read endpoints are open (no authentication required). In production, replace the key via the `API_KEY` environment variable.

---

### Ingestion Service API

**Base URL:** `http://localhost:8000/api/v1`

#### Locations

| Method   | Endpoint          | Auth | Description               |
| -------- | ----------------- | ---- | ------------------------- |
| `GET`    | `/locations`      | No   | List all active locations |
| `POST`   | `/locations`      | Yes  | Register a new location   |
| `GET`    | `/locations/{id}` | No   | Get a location by ID      |
| `PUT`    | `/locations/{id}` | Yes  | Update a location         |
| `DELETE` | `/locations/{id}` | Yes  | Soft-delete a location    |

**Create a location:**

```bash
curl -X POST http://localhost:8000/api/v1/locations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-key" \
  -d '{
    "name": "Medellín",
    "latitude": 6.2442,
    "longitude": -75.5812,
    "timezone": "America/Bogota"
  }'
```

#### Observations

| Method | Endpoint               | Auth | Description                                                       |
| ------ | ---------------------- | ---- | ----------------------------------------------------------------- |
| `GET`  | `/observations`        | No   | List raw observations (`limit`, `offset`, `since`, `location_id`) |
| `GET`  | `/observations/{id}`   | No   | Get a single raw observation                                      |
| `POST` | `/observations/ingest` | Yes  | Manually trigger an ingestion cycle                               |

**List observations since a timestamp:**

```bash
curl "http://localhost:8000/api/v1/observations?since=2026-06-30T00:00:00Z&limit=50"
```

---

### Processing Service API

**Base URL:** `http://localhost:8001/api/v1`

#### Processing Rules

| Method   | Endpoint      | Auth | Description    |
| -------- | ------------- | ---- | -------------- |
| `GET`    | `/rules`      | No   | List all rules |
| `POST`   | `/rules`      | Yes  | Create a rule  |
| `PUT`    | `/rules/{id}` | Yes  | Update a rule  |
| `DELETE` | `/rules/{id}` | Yes  | Delete a rule  |

**Create a rule:**

```bash
curl -X POST http://localhost:8001/api/v1/rules \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-key" \
  -d '{
    "metric": "temperature_c",
    "operator": ">=",
    "threshold": 35.0,
    "severity": "HIGH",
    "alert_type": "HIGH_TEMPERATURE",
    "message_template": "Temperature of {value}°C exceeds threshold of {threshold}°C"
  }'
```

Valid operators: `>`, `>=`, `<`, `<=`, `==`

#### Processed Observations

| Method | Endpoint          | Auth | Description                                      |
| ------ | ----------------- | ---- | ------------------------------------------------ |
| `GET`  | `/processed`      | No   | List processed observations                      |
| `GET`  | `/processed/{id}` | No   | Get a processed observation with derived metrics |

#### Alerts

| Method  | Endpoint                   | Auth | Description                                      |
| ------- | -------------------------- | ---- | ------------------------------------------------ |
| `GET`   | `/alerts`                  | No   | List alerts (`severity`, `acknowledged` filters) |
| `GET`   | `/alerts/{id}`             | No   | Get a single alert                               |
| `PATCH` | `/alerts/{id}/acknowledge` | Yes  | Acknowledge an alert                             |

#### Processing Control

| Method | Endpoint   | Auth | Description                         |
| ------ | ---------- | ---- | ----------------------------------- |
| `POST` | `/process` | Yes  | Manually trigger a processing cycle |

---

## Data Model

### `ingestion` schema

```sql
locations (
    id              UUID PRIMARY KEY,
    name            VARCHAR NOT NULL,
    latitude        FLOAT NOT NULL,
    longitude       FLOAT NOT NULL,
    timezone        VARCHAR DEFAULT 'UTC',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP
)

raw_observations (
    id              UUID PRIMARY KEY,
    location_id     UUID REFERENCES locations ON DELETE RESTRICT,
    observed_at     TIMESTAMP NOT NULL,
    temperature_c   FLOAT,
    humidity_pct    FLOAT,
    wind_speed_kmh  FLOAT,
    precipitation_mm FLOAT,
    weather_code    INT,
    ingested_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (location_id, observed_at)   -- idempotency guarantee
)
```

### `processing` schema

```sql
processing_rules (
    id               UUID PRIMARY KEY,
    metric           VARCHAR NOT NULL,
    operator         VARCHAR CHECK (operator IN ('>', '>=', '<', '<=', '==')),
    threshold        FLOAT NOT NULL,
    severity         VARCHAR NOT NULL,
    alert_type       VARCHAR NOT NULL,
    message_template TEXT NOT NULL,
    is_active        BOOLEAN DEFAULT TRUE,
    created_at / updated_at TIMESTAMP
)

processed_observations (
    id                  UUID PRIMARY KEY,
    raw_observation_id  UUID UNIQUE,           -- idempotency guard
    location_id         UUID NOT NULL,
    observed_at         TIMESTAMP NOT NULL,
    -- raw fields
    temperature_c, humidity_pct, wind_speed_kmh, precipitation_mm, weather_code,
    -- derived metrics
    heat_index_c        FLOAT,
    wind_chill_c        FLOAT,
    feels_like_c        FLOAT,
    severity_score      INT DEFAULT 0,
    processed_at        TIMESTAMP DEFAULT NOW()
)

alerts (
    id                       UUID PRIMARY KEY,
    processed_observation_id UUID REFERENCES processed_observations,
    rule_id                  UUID REFERENCES processing_rules,
    alert_type               VARCHAR NOT NULL,
    severity                 VARCHAR NOT NULL,
    message                  TEXT NOT NULL,
    acknowledged             BOOLEAN DEFAULT FALSE,
    created_at               TIMESTAMP,
    acknowledged_at          TIMESTAMP
)

watermarks (
    id               UUID PRIMARY KEY,
    source           VARCHAR UNIQUE NOT NULL,   -- 'ingestion-service'
    last_ingested_at TIMESTAMP NOT NULL,
    updated_at       TIMESTAMP
)
```

---

## Testing

Unit tests use **in-memory fakes** — no database, no HTTP calls, no mocks. The test suite validates use case logic in complete isolation.

```bash
# Run tests for ingestion service
docker compose exec ingestion-service pytest tests/unit -v

# Run tests for processing service
docker compose exec processing-service pytest tests/unit -v

# Or locally (with venv activated)
cd ingestion-service && pytest tests/unit -v
cd processing-service && pytest tests/unit -v
```

**Test coverage highlights (ingestion service):**

| Test file                     | Scenarios covered                                                                                                                    |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `test_ingest_observations.py` | Fetches only active locations, stores results, ignores duplicates (idempotency), handles empty location list, records adapter errors |
| `test_list_observations.py`   | Returns all observations, pagination, filter by location, filter by `since`                                                          |
| `test_register_location.py`   | Creates with defaults, persists in repo, custom timezone                                                                             |
| `test_locations.py`           | Get found/not found (404), list active only, update, soft delete                                                                     |

**Testing philosophy:** fakes are defined in `tests/unit/fakes.py` and implement the same `Protocol` contracts as the real SQLAlchemy repositories. This means the test suite validates the exact same use case code that runs in production — with zero infrastructure dependencies.

---

## Design Decisions (ADRs)

All architectural decisions are documented as Architecture Decision Records in [`docs/adr/`](docs/adr/). Summary:

| ADR                                                              | Decision                                       | Key Reason                                            |
| ---------------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------- |
| [0001](docs/adr/0001-use-fastapi.md)                             | FastAPI for both services                      | Async-native, first-class DI, automatic OpenAPI       |
| [0002](docs/adr/0002-use-sqlalchemy.md)                          | SQLAlchemy 2 + asyncpg + Alembic               | Mature async ORM, version-controlled migrations       |
| [0003](docs/adr/0003-split-into-two-microservices.md)            | Two microservices                              | Clear separation of ingestion vs. processing concerns |
| [0004](docs/adr/0004-rest-communication-instead-of-messaging.md) | REST HTTP polling between services             | Simplicity; SQS planned for future                    |
| [0005](docs/adr/0005-postgresql-as-primary-database.md)          | PostgreSQL, separate schemas                   | ACID guarantees, schema isolation without two DBs     |
| [0006](docs/adr/0006-docker-compose-for-local-development.md)    | Docker Compose for local dev                   | Single-command reproducible environment               |
| [0007](docs/adr/0007-aws-ecs-fargate.md)                         | AWS ECS Fargate for production                 | Serverless containers, no EC2 management              |
| [0008](docs/adr/0008-aws-cdk-for-infrastructure.md)              | AWS CDK (TypeScript) for IaC                   | Type-safe, reproducible cloud infrastructure          |
| [0009](docs/adr/0009-open-meteo-as-external-provider.md)         | Open-Meteo as weather provider                 | Free, no API key, global coverage, adapter pattern    |
| [0010](docs/adr/0010-repository-pattern.md)                      | Repository Pattern                             | Decouples domain from persistence; enables fakes      |
| [0011](docs/adr/0011-anti-join-for-unprocessed-tracking.md)      | Watermark + anti-join for unprocessed tracking | Efficient, stateless progress tracking                |

---

## Planned Infrastructure (AWS)

The production deployment is designed around AWS managed services (not yet implemented — documented in ADRs 0007 and 0008):

```
Internet → ALB → ECS Fargate (ingestion-service)
                 ECS Fargate (processing-service)
                          │
                 Aurora Serverless v2 (PostgreSQL)
                          │
                   ECR (container images)
                   CloudWatch (logs + metrics)
```

**Planned CDK stacks:**

- `NetworkStack` — VPC, public subnets (no NAT to minimize cost)
- `DatabaseStack` — Aurora Serverless v2, parameter groups
- `ServiceStack` — ECS Cluster, Task Definitions, Services, ALB
- `MonitoringStack` — CloudWatch dashboards, alarms

**Estimated cost:** ~$80/month for a minimal production setup.

---

## Future Improvements

- **Event-driven architecture** — replace HTTP polling with AWS SQS/EventBridge for reliable, decoupled ingestion events
- **Alert notifications** — push alerts via SNS, email, or webhook when thresholds are crossed
- **Redis caching** — cache frequently-read rule sets and location lists
- **Full authentication** — JWT-based auth with user management, replacing the static API key
- **Horizontal scaling** — stateless design already supports multiple replicas; needs distributed locking for scheduler deduplication
- **CI/CD pipeline** — GitHub Actions for test, build, push to ECR, and deploy to ECS
- **Observability** — structured logging (JSON), distributed tracing, CloudWatch dashboards
- **Data retention** — automated cleanup jobs (90-day raw observations, 365-day processed data)
- **CDK implementation** — materialize the planned AWS infrastructure as code

---

## Environment Variables Reference

| Variable                      | Service    | Default                      | Description                              |
| ----------------------------- | ---------- | ---------------------------- | ---------------------------------------- |
| `API_KEY`                     | Both       | —                            | Secret for write endpoint authentication |
| `DATABASE_URL`                | Both       | —                            | asyncpg connection string                |
| `DATABASE_POOL_SIZE`          | Both       | `5`                          | SQLAlchemy connection pool size          |
| `DATABASE_MAX_OVERFLOW`       | Both       | `5`                          | Max connections beyond pool size         |
| `LOG_LEVEL`                   | Both       | `INFO`                       | Python log level                         |
| `INGESTION_SCHEMA`            | Ingestion  | `ingestion`                  | PostgreSQL schema name                   |
| `OPEN_METEO_BASE_URL`         | Ingestion  | `https://api.open-meteo.com` | Weather API base URL                     |
| `INGESTION_INTERVAL_SECONDS`  | Ingestion  | `900`                        | Polling interval (15 min)                |
| `PROCESSING_SCHEMA`           | Processing | `processing`                 | PostgreSQL schema name                   |
| `INGESTION_SERVICE_URL`       | Processing | `http://localhost:8000`      | Ingestion service base URL               |
| `PROCESSING_INTERVAL_SECONDS` | Processing | `300`                        | Processing interval (5 min)              |

---

_Built by Juan Pablo Jiménez — [linkedin.com/in/juanpablojimenezheredia](https://linkedin.com/in/juanpablojimenezheredia)_
