# Weather Middleware Platform -- Architecture Overview

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Business Problem](#2-business-problem)
3. [System Goals](#3-system-goals)
4. [Architecture Principles](#4-architecture-principles)
5. [High-Level Architecture](#5-high-level-architecture)
6. [Service Responsibilities](#6-service-responsibilities)
7. [Request Lifecycle](#7-request-lifecycle)
8. [Data Model Overview](#8-data-model-overview)
9. [Deployment Architecture](#9-deployment-architecture)
10. [Local Development](#10-local-development)
11. [Future Improvements](#11-future-improvements)
12. [Trade-offs](#12-trade-offs)
13. [Glossary](#13-glossary)

---

## 1. Project Overview

The Weather Middleware Platform is a backend system composed of two microservices that periodically ingest real weather observations from the [Open-Meteo API](https://open-meteo.com/), persist them, apply configurable business rules, generate weather alerts, and expose processed information through REST APIs.

The architecture intentionally mirrors enterprise middleware systems -- specifically laboratory integration platforms -- where an external instrument (here, a weather API) produces raw data, a middleware layer normalizes and stores it, and a processing engine applies domain rules before surfacing results to downstream consumers.

This project exists for two purposes:

1. **Learning.** Practice FastAPI, SQLAlchemy 2, Alembic, Docker, AWS ECS, and AWS CDK in a realistic distributed system.
2. **Portfolio.** Demonstrate backend engineering practices -- clean architecture, dependency injection, repository pattern, container-first design, infrastructure-as-code -- in a codebase that a reviewer can clone and run locally in under five minutes.

---

## 2. Business Problem

Enterprise middleware systems sit between data producers and data consumers. In a clinical laboratory, instruments generate raw test results; middleware normalizes, validates, and enriches those results before forwarding them to a Laboratory Information System (LIS). The middleware is responsible for:

- **Reliable ingestion** -- polling instruments on a schedule, handling timeouts and retries.
- **Normalization** -- translating vendor-specific formats into a canonical schema.
- **Business rule execution** -- flagging abnormal results, applying delta checks, triggering alerts.
- **Auditability** -- preserving every raw observation exactly as received.

This project maps that pattern onto the weather domain:

| Laboratory Middleware        | Weather Middleware Platform     |
| ---------------------------- | ------------------------------ |
| Instrument                   | Open-Meteo API                 |
| Raw test result              | Raw weather observation        |
| Normalization engine         | ingestion-service              |
| Business rule engine         | processing-service             |
| Abnormal flag / delta check  | Weather alert                  |
| LIS consumer                 | REST API consumer              |

The domain is simpler, but the engineering challenges -- polling external systems, schema evolution, stateless processing, containerized deployment -- are identical.

---

## 3. System Goals

### Functional Requirements

| ID   | Requirement                                                                                     |
| ---- | ----------------------------------------------------------------------------------------------- |
| FR-1 | Periodically retrieve current and hourly weather observations from Open-Meteo for configured locations. |
| FR-2 | Persist every raw observation immutably.                                                        |
| FR-3 | Expose CRUD endpoints for locations and raw observations.                                       |
| FR-4 | Consume raw observations via REST and apply configurable business rules.                        |
| FR-5 | Calculate derived metrics: severity score, heat index, wind chill, feels-like temperature.       |
| FR-6 | Generate alerts when observations breach configured thresholds.                                 |
| FR-7 | Expose REST endpoints for processed observations, alerts, and processing rules.                 |

### Non-Functional Requirements

| ID    | Requirement                                                                                  |
| ----- | -------------------------------------------------------------------------------------------- |
| NFR-1 | Each service starts and responds to health checks within 10 seconds.                         |
| NFR-2 | Services are stateless; any instance can be replaced without data loss.                      |
| NFR-3 | Local development requires only Docker and Docker Compose.                                   |
| NFR-4 | Infrastructure is defined entirely in code (AWS CDK).                                        |
| NFR-5 | Database schema changes are managed through versioned migrations (Alembic).                   |
| NFR-6 | The system tolerates Open-Meteo downtime gracefully (retries, circuit-breaker-ready design).  |

### Learning Objectives

FastAPI, SQLAlchemy 2, Alembic, microservice decomposition, Docker, Docker Compose, AWS ECS Fargate, AWS CDK (TypeScript), Aurora PostgreSQL, REST inter-service communication, Clean Architecture, dependency injection, and the repository pattern.

---

## 4. Architecture Principles

### SOLID

Each service is structured so that classes have a single reason to change (SRP), new behavior is added by extending rather than modifying existing code (OCP), abstractions are defined as Python protocols or abstract base classes (DIP), and interfaces are kept narrow (ISP). Liskov substitutability is maintained by ensuring repository implementations are interchangeable behind their protocol.

**Why.** SOLID produces code that is testable in isolation, safe to refactor, and readable by engineers who did not write it. In a portfolio project, this signals professional discipline.

### Clean Architecture

Dependencies point inward. The domain layer (entities, value objects, business rules) has zero imports from frameworks or infrastructure. Use cases orchestrate domain logic. Adapters (FastAPI routes, SQLAlchemy repositories, httpx clients) live at the outer ring.

**Why.** Decoupling the domain from the framework means the core logic can be tested without spinning up a database or HTTP server. It also makes framework migrations (e.g., FastAPI to Litestar) a localized change.

### 12-Factor App

Configuration is injected via environment variables. Logs are written to stdout. Each service is a single stateless process. Dependencies are explicitly declared in `requirements.txt`. Dev/prod parity is maintained through Docker.

**Why.** 12-Factor is the baseline contract for deploying applications on container orchestrators like ECS. Violating it creates operational friction that compounds in production.

### Repository Pattern

Data access is encapsulated behind repository protocols (`ObservationRepository`, `AlertRepository`, etc.). Use cases depend on the protocol, not on SQLAlchemy directly.

**Why.** This makes it possible to swap the persistence layer (e.g., replace PostgreSQL with DynamoDB for a specific table) without touching business logic. More immediately, it enables unit tests with in-memory fakes.

### Dependency Injection

FastAPI's `Depends()` mechanism wires repositories and use cases at the router level. A `dependencies.py` module in each service acts as the composition root.

**Why.** Explicit wiring makes the object graph visible and testable. It avoids hidden global state and makes it trivial to substitute test doubles.

### Stateless Services

No in-process caches, no sticky sessions, no local file storage. All state lives in PostgreSQL.

**Why.** Statelessness is a prerequisite for horizontal scaling on Fargate. It also simplifies deployments: rolling updates replace tasks without draining state.

### Container-First Design

Each service ships as a Docker image. The Dockerfile is the single source of truth for the runtime environment. There is no "run natively on the host" path for production.

**Why.** Containers eliminate environment drift between development and production. On ECS Fargate, the container *is* the deployment unit.

---

## 5. High-Level Architecture

### C4-Inspired Container Diagram

```mermaid
graph TB
    subgraph external [External Systems]
        OpenMeteo["Open-Meteo API\n(Weather Data Provider)"]
    end

    subgraph platform [Weather Middleware Platform]
        Ingestion["ingestion-service\n(FastAPI)"]
        Processing["processing-service\n(FastAPI)"]
        DB[("Aurora PostgreSQL\ningestion | processing schemas")]
    end

    subgraph consumers [API Consumers]
        Client["REST Client\n(curl / frontend / other service)"]
    end

    Ingestion -->|"GET /v1/forecast\n(scheduled poll)"| OpenMeteo
    Ingestion -->|"INSERT raw observations\n(ingestion schema)"| DB
    Processing -->|"GET /api/v1/observations\n(scheduled poll)"| Ingestion
    Processing -->|"INSERT processed data + alerts\n(processing schema)"| DB
    Client -->|"GET /api/v1/...\n(on demand)"| Ingestion
    Client -->|"GET /api/v1/...\n(on demand)"| Processing
```

### How It Fits Together

1. **Open-Meteo** is the external data source. It provides a free, keyless JSON API returning current conditions and hourly forecasts for any coordinate pair.
2. **ingestion-service** owns data acquisition. A background scheduler (configurable interval, default 15 minutes) polls Open-Meteo for each configured location, normalizes the JSON response into a canonical `RawObservation` entity, and persists it. It also exposes CRUD endpoints so the processing-service (or any client) can query raw data.
3. **processing-service** owns data enrichment. Its own scheduler polls ingestion-service for unprocessed observations, runs business rules, computes derived metrics, generates alerts, and persists the results. It exposes endpoints for processed observations, alerts, and rule management.
4. **Aurora PostgreSQL** stores all persistent state. The two services use separate schemas (`ingestion`, `processing`) within the same database cluster. This enforces logical boundaries without the operational overhead of two database instances.

---

## 6. Service Responsibilities

### ingestion-service

**Purpose.** Acquire, normalize, and store raw weather observations. Serve them via REST.

**Endpoints (planned):**

| Method | Path                            | Description                            |
| ------ | ------------------------------- | -------------------------------------- |
| GET    | `/api/v1/locations`             | List all configured locations          |
| POST   | `/api/v1/locations`             | Register a new location                |
| GET    | `/api/v1/locations/{id}`        | Get a single location                  |
| PUT    | `/api/v1/locations/{id}`        | Update a location                      |
| DELETE | `/api/v1/locations/{id}`        | Soft-delete a location                 |
| GET    | `/api/v1/observations`          | List raw observations (filterable)     |
| GET    | `/api/v1/observations/{id}`     | Get a single raw observation           |
| POST   | `/api/v1/observations/ingest`   | Manually trigger ingestion             |
| GET    | `/health`                       | Liveness check                         |

**Internal layers:**

```
ingestion-service/
├── src/
│   ├── domain/           # Entities, value objects, repository protocols
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── repositories/
│   ├── application/      # Use cases, DTOs
│   │   ├── use_cases/
│   │   └── dtos/
│   ├── infrastructure/   # SQLAlchemy models, repository implementations, httpx client
│   │   ├── persistence/
│   │   ├── external/     # Open-Meteo client adapter
│   │   └── config/
│   └── interface/        # FastAPI routers, schemas, dependencies
│       ├── api/
│       └── dependencies.py
├── alembic/
├── tests/
├── Dockerfile
└── requirements.txt
```

**Key design decisions:**

- Raw observations are **immutable**. Once inserted, they are never updated or deleted. This mirrors the auditability requirement of laboratory middleware where original instrument readings must be preserved verbatim.
- The Open-Meteo client is an **adapter** behind a protocol (`WeatherDataSource`). Swapping to a different provider (e.g., OpenWeatherMap) means writing a new adapter, not changing business logic.
- Ingestion runs on a **background task** inside the FastAPI process using a lightweight scheduler (e.g., `asyncio` loop with configurable interval). This avoids adding a separate worker process for a simple periodic job.

### processing-service

**Purpose.** Consume raw observations, apply business rules, generate alerts, and serve processed data via REST.

**Endpoints (planned):**

| Method | Path                                 | Description                              |
| ------ | ------------------------------------ | ---------------------------------------- |
| GET    | `/api/v1/processed`                  | List processed observations (filterable) |
| GET    | `/api/v1/processed/{id}`             | Get a single processed observation       |
| GET    | `/api/v1/alerts`                     | List alerts (filterable by severity, ack) |
| GET    | `/api/v1/alerts/{id}`                | Get a single alert                       |
| PATCH  | `/api/v1/alerts/{id}/acknowledge`    | Acknowledge an alert                     |
| GET    | `/api/v1/rules`                      | List processing rules                    |
| POST   | `/api/v1/rules`                      | Create a processing rule                 |
| PUT    | `/api/v1/rules/{id}`                 | Update a processing rule                 |
| DELETE | `/api/v1/rules/{id}`                 | Delete a processing rule                 |
| POST   | `/api/v1/process`                    | Manually trigger processing cycle        |
| GET    | `/health`                            | Liveness check                           |

**Internal layers:**

```
processing-service/
├── src/
│   ├── domain/           # Entities, value objects, repository protocols, rule engine protocol
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── repositories/
│   ├── application/      # Use cases, DTOs
│   │   ├── use_cases/
│   │   └── dtos/
│   ├── infrastructure/   # SQLAlchemy models, repository implementations, ingestion client
│   │   ├── persistence/
│   │   ├── external/     # httpx client calling ingestion-service
│   │   └── config/
│   └── interface/        # FastAPI routers, schemas, dependencies
│       ├── api/
│       └── dependencies.py
├── alembic/
├── tests/
├── Dockerfile
└── requirements.txt
```

**Key design decisions:**

- The processing-service **never calls Open-Meteo directly**. All weather data flows through ingestion-service. This enforces a clear data ownership boundary: ingestion-service is the system of record for raw data.
- Business rules are **data-driven**. Rules are stored in the `processing_rules` table and evaluated at runtime. Adding a new threshold check requires an API call, not a code deployment.
- The rule engine is a **pure domain function** that takes an observation and a list of rules, and returns a list of alerts. No I/O inside the engine. This makes it trivially testable.

---

## 7. Request Lifecycle

### Ingestion Flow

```mermaid
sequenceDiagram
    participant Scheduler as Ingestion Scheduler
    participant Ingestion as ingestion-service
    participant OpenMeteo as Open-Meteo API
    participant DB as PostgreSQL

    Scheduler->>Ingestion: trigger ingestion cycle
    Ingestion->>DB: SELECT active locations
    DB-->>Ingestion: locations list

    loop For each location
        Ingestion->>OpenMeteo: GET /v1/forecast?lat=...&lon=...&current=...&hourly=...
        OpenMeteo-->>Ingestion: JSON response (current + hourly data)
        Ingestion->>Ingestion: normalize response into RawObservation entities
        Ingestion->>DB: INSERT INTO ingestion.raw_observations
        DB-->>Ingestion: confirm write
    end

    Ingestion->>Ingestion: log cycle summary (locations processed, observations stored)
```

### Processing Flow

```mermaid
sequenceDiagram
    participant Scheduler as Processing Scheduler
    participant Processing as processing-service
    participant Ingestion as ingestion-service
    participant DB as PostgreSQL

    Scheduler->>Processing: trigger processing cycle
    Processing->>Ingestion: GET /api/v1/observations?status=unprocessed
    Ingestion-->>Processing: list of raw observations

    loop For each observation
        Processing->>DB: SELECT active rules FROM processing.processing_rules
        DB-->>Processing: rules list
        Processing->>Processing: evaluate rules against observation
        Processing->>Processing: compute derived metrics (heat index, wind chill, severity)
        Processing->>DB: INSERT INTO processing.processed_observations
        DB-->>Processing: confirm write

        alt Thresholds breached
            Processing->>DB: INSERT INTO processing.alerts
            DB-->>Processing: confirm write
        end
    end

    Processing->>Processing: log cycle summary (observations processed, alerts generated)
```

### Step-by-Step Narrative

1. **Ingestion scheduler fires** (default: every 15 minutes). It queries the `locations` table for all active locations.
2. **For each location**, the ingestion-service sends a GET request to Open-Meteo's `/v1/forecast` endpoint with the location's coordinates and the desired weather variables (`temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`, `precipitation`, `weather_code`).
3. The **Open-Meteo adapter** normalizes the JSON response into one or more `RawObservation` domain entities. The adapter isolates the rest of the system from Open-Meteo's response format.
4. Each `RawObservation` is **persisted** to `ingestion.raw_observations`. The row is immutable and timestamped with both `observed_at` (from the API) and `ingested_at` (server clock).
5. **Processing scheduler fires** (default: every 5 minutes, offset from ingestion). It calls the ingestion-service's REST API to fetch observations that have not yet been processed, using a query parameter or a watermark timestamp.
6. **For each observation**, the processing-service loads active rules from `processing.processing_rules` and feeds the observation and rules into the **rule engine** -- a pure function that returns a severity score, derived metrics, and a (possibly empty) list of alerts.
7. The **processed observation** (with severity score and derived metrics) is persisted to `processing.processed_observations`.
8. Any **alerts** generated by the rule engine are persisted to `processing.alerts` with an `acknowledged = false` default.
9. API consumers can query both services at any time. The ingestion-service serves raw data; the processing-service serves enriched data and alerts.

---

## 8. Data Model Overview

### ingestion schema

#### locations

| Column      | Type                     | Constraints                | Notes                              |
| ----------- | ------------------------ | -------------------------- | ---------------------------------- |
| id          | UUID                     | PK, default gen_random_uuid() | Avoids sequential ID leakage    |
| name        | VARCHAR(255)             | NOT NULL                   | Human-readable (e.g., "Miami, FL") |
| latitude    | DOUBLE PRECISION         | NOT NULL                   | WGS84                             |
| longitude   | DOUBLE PRECISION         | NOT NULL                   | WGS84                             |
| timezone    | VARCHAR(64)              | NOT NULL, default 'UTC'    | IANA timezone identifier           |
| is_active   | BOOLEAN                  | NOT NULL, default TRUE     | Soft-delete / disable              |
| created_at  | TIMESTAMP WITH TIME ZONE | NOT NULL, default now()    |                                    |
| updated_at  | TIMESTAMP WITH TIME ZONE | NOT NULL, default now()    |                                    |

#### raw_observations

| Column           | Type                     | Constraints                | Notes                                     |
| ---------------- | ------------------------ | -------------------------- | ----------------------------------------- |
| id               | UUID                     | PK, default gen_random_uuid() |                                        |
| location_id      | UUID                     | FK -> locations.id, NOT NULL | Cascading reference                     |
| temperature_c    | DOUBLE PRECISION         |                            | Celsius, nullable if API omits            |
| humidity_pct     | DOUBLE PRECISION         |                            | Relative humidity 0-100                   |
| wind_speed_kmh   | DOUBLE PRECISION         |                            | km/h                                      |
| precipitation_mm | DOUBLE PRECISION         |                            | mm                                        |
| weather_code     | INTEGER                  |                            | WMO weather interpretation code           |
| observed_at      | TIMESTAMP WITH TIME ZONE | NOT NULL                   | Timestamp from the weather API            |
| ingested_at      | TIMESTAMP WITH TIME ZONE | NOT NULL, default now()    | Server-side timestamp at write time       |

**Indexes:**
- `ix_raw_observations_location_id` on `location_id` -- accelerates per-location queries.
- `ix_raw_observations_observed_at` on `observed_at` -- accelerates time-range filters.
- `ix_raw_observations_ingested_at` on `ingested_at` -- used by the processing-service watermark query.

**Why UUIDs.** UUIDs as primary keys avoid exposing sequential IDs in REST responses (security best practice) and simplify future scenarios where observations might be generated by multiple ingestion instances without coordination. The trade-off is slightly larger index size compared to BIGINT, which is negligible at the expected data volumes.

### processing schema

#### processed_observations

| Column                | Type                     | Constraints                        | Notes                                  |
| --------------------- | ------------------------ | ---------------------------------- | -------------------------------------- |
| id                    | UUID                     | PK, default gen_random_uuid()      |                                        |
| raw_observation_id    | UUID                     | NOT NULL, UNIQUE                   | Logical FK to ingestion.raw_observations; not enforced across schemas |
| location_id           | UUID                     | NOT NULL                           | Denormalized for query convenience     |
| temperature_c         | DOUBLE PRECISION         |                                    | Copied from raw                        |
| humidity_pct          | DOUBLE PRECISION         |                                    | Copied from raw                        |
| wind_speed_kmh        | DOUBLE PRECISION         |                                    | Copied from raw                        |
| precipitation_mm      | DOUBLE PRECISION         |                                    | Copied from raw                        |
| weather_code          | INTEGER                  |                                    | Copied from raw                        |
| heat_index_c          | DOUBLE PRECISION         |                                    | Calculated derived metric              |
| wind_chill_c          | DOUBLE PRECISION         |                                    | Calculated derived metric              |
| feels_like_c          | DOUBLE PRECISION         |                                    | Calculated derived metric              |
| severity_score        | INTEGER                  | NOT NULL, CHECK (0..10)            | 0 = benign, 10 = extreme              |
| observed_at           | TIMESTAMP WITH TIME ZONE | NOT NULL                           |                                        |
| processed_at          | TIMESTAMP WITH TIME ZONE | NOT NULL, default now()            |                                        |

**Why denormalize.** The processing schema copies key fields from the raw observation rather than joining across schemas at query time. This keeps each schema self-contained and eliminates cross-schema joins, which would couple the two services at the database level.

#### alerts

| Column                | Type                     | Constraints                        | Notes                                  |
| --------------------- | ------------------------ | ---------------------------------- | -------------------------------------- |
| id                    | UUID                     | PK, default gen_random_uuid()      |                                        |
| processed_observation_id | UUID                  | FK -> processed_observations.id    |                                        |
| rule_id               | UUID                     | FK -> processing_rules.id          | Which rule triggered this alert        |
| alert_type            | VARCHAR(64)              | NOT NULL                           | e.g., "HIGH_TEMPERATURE", "STORM"      |
| severity              | VARCHAR(16)              | NOT NULL                           | "LOW", "MEDIUM", "HIGH", "CRITICAL"    |
| message               | TEXT                     | NOT NULL                           | Human-readable alert description       |
| acknowledged          | BOOLEAN                  | NOT NULL, default FALSE            |                                        |
| created_at            | TIMESTAMP WITH TIME ZONE | NOT NULL, default now()            |                                        |
| acknowledged_at       | TIMESTAMP WITH TIME ZONE |                                    | NULL until acknowledged                |

**Indexes:**
- `ix_alerts_severity` on `severity` -- supports filtering dashboards by severity level.
- `ix_alerts_acknowledged` on `acknowledged` -- fast lookup of unacknowledged alerts.

#### processing_rules

| Column         | Type                     | Constraints                   | Notes                                        |
| -------------- | ------------------------ | ----------------------------- | -------------------------------------------- |
| id             | UUID                     | PK, default gen_random_uuid() |                                              |
| metric         | VARCHAR(64)              | NOT NULL                      | Field name (e.g., "temperature_c")           |
| operator       | VARCHAR(4)               | NOT NULL                      | One of: ">", ">=", "<", "<=", "=="           |
| threshold      | DOUBLE PRECISION         | NOT NULL                      | Value to compare against                     |
| severity       | VARCHAR(16)              | NOT NULL                      | Alert severity if rule fires                 |
| alert_type     | VARCHAR(64)              | NOT NULL                      | Alert type label                             |
| message_template | TEXT                   | NOT NULL                      | Template with `{value}` and `{threshold}` placeholders |
| is_active      | BOOLEAN                  | NOT NULL, default TRUE        |                                              |
| created_at     | TIMESTAMP WITH TIME ZONE | NOT NULL, default now()       |                                              |
| updated_at     | TIMESTAMP WITH TIME ZONE | NOT NULL, default now()       |                                              |

**Why data-driven rules.** Hardcoding thresholds in application code requires a deployment for every threshold change. Storing rules in the database allows operators to adjust thresholds at runtime via the REST API. The trade-off is increased complexity in the rule engine, but the engine itself remains a pure function that is straightforward to test.

---

## 9. Deployment Architecture

### Deployment Diagram

```mermaid
graph TB
    subgraph vpc [VPC]
        subgraph publicSubnets [Public Subnets - 2 AZs]
            subgraph ecs [ECS Cluster - Fargate]
                IngestionTask["ingestion-service\nFargate Task\nPort 8000"]
                ProcessingTask["processing-service\nFargate Task\nPort 8001"]
            end
            ALB["Application Load Balancer\n(internal)"]
        end

        subgraph privateSubnets [Private Subnets - 2 AZs]
            Aurora[("Aurora PostgreSQL\nServerless v2")]
        end
    end

    subgraph aws [AWS Services]
        ECR["Amazon ECR\n(Container Registry)"]
        CloudWatch["CloudWatch Logs"]
    end

    subgraph external [External]
        OpenMeteo["Open-Meteo API"]
        GitHub["GitHub Actions\n(future CI/CD)"]
    end

    ALB --> IngestionTask
    ALB --> ProcessingTask
    ProcessingTask -->|"REST via ALB"| IngestionTask
    IngestionTask --> Aurora
    ProcessingTask --> Aurora
    IngestionTask --> CloudWatch
    ProcessingTask --> CloudWatch
    IngestionTask -->|"HTTPS"| OpenMeteo
    ECR -->|"pull images"| ecs
    GitHub -->|"push images"| ECR
```

### CDK Stack Structure

The infrastructure is defined in a single CDK app (TypeScript) with logically separated constructs:

| Construct           | Resources                                                                 |
| ------------------- | ------------------------------------------------------------------------- |
| `NetworkStack`      | VPC, 2 public subnets, 2 private subnets, security groups                |
| `DatabaseStack`     | Aurora PostgreSQL Serverless v2 cluster, subnet group, secrets            |
| `ServiceStack`      | ECS cluster, ECR repositories, Fargate task definitions, ALB, services   |
| `MonitoringStack`   | CloudWatch log groups, basic alarms (CPU, memory, 5xx count)             |

**Why a single CDK app with constructs (not separate apps).** Constructs within one app can share references (VPC ID, security group, database endpoint) through standard CDK cross-construct references. Separate apps would require SSM parameters or CloudFormation exports, adding operational overhead without benefit at this scale.

### Networking Decisions

**Fargate tasks in public subnets with `assignPublicIp: true`.**

- **Benefit:** Eliminates the need for a NAT Gateway, which costs ~$32/month per AZ and is disproportionate for a portfolio project.
- **Drawback:** Tasks are directly addressable on the internet, though security groups restrict inbound traffic to the ALB only.
- **Alternative:** Private subnets + NAT Gateway. This is the production best practice for services that should not have public IPs.
- **Why this wins here:** Cost. The security group rules provide sufficient isolation for a portfolio/learning project. The architecture document explicitly acknowledges this trade-off so a reviewer sees the candidate understands the production pattern.

**Aurora PostgreSQL in private subnets.**

- The database has no public IP. Fargate tasks reach it through VPC-internal networking. Security groups restrict inbound traffic to port 5432 from the ECS security group only.

**Internal ALB for inter-service communication.**

- The processing-service calls ingestion-service through the ALB's DNS name, not through direct task IPs. This decouples service discovery from ECS task lifecycle (tasks can be replaced without breaking the caller).
- **Alternative:** AWS Cloud Map (service discovery). More elegant, but adds a dependency and configuration surface. The ALB approach is simpler and provides built-in health checking.

### Environment Configuration

All configuration is injected as environment variables into Fargate task definitions:

| Variable               | Example Value                             | Used By            |
| ---------------------- | ----------------------------------------- | ------------------- |
| `DATABASE_URL`         | `postgresql+asyncpg://user:pass@host/db`  | Both                |
| `INGESTION_SCHEMA`     | `ingestion`                               | ingestion-service   |
| `PROCESSING_SCHEMA`    | `processing`                              | processing-service  |
| `INGESTION_SERVICE_URL`| `http://internal-alb-dns:8000`            | processing-service  |
| `OPEN_METEO_BASE_URL`  | `https://api.open-meteo.com`              | ingestion-service   |
| `INGESTION_INTERVAL_SECONDS` | `900`                               | ingestion-service   |
| `PROCESSING_INTERVAL_SECONDS` | `300`                             | processing-service  |
| `LOG_LEVEL`            | `INFO`                                    | Both                |

Database credentials are stored in AWS Secrets Manager (created by the Aurora CDK construct) and injected into the task definition as secrets, not plain environment variables.

---

## 10. Local Development

### Docker Compose

```yaml
# docker-compose.yml (structure, not verbatim)
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: weather
      POSTGRES_PASSWORD: weather
      POSTGRES_DB: weather_middleware
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  ingestion-service:
    build: ./ingestion-service
    environment:
      DATABASE_URL: postgresql+asyncpg://weather:weather@postgres:5432/weather_middleware
      INGESTION_SCHEMA: ingestion
      OPEN_METEO_BASE_URL: https://api.open-meteo.com
      INGESTION_INTERVAL_SECONDS: 900
      LOG_LEVEL: DEBUG
    ports:
      - "8000:8000"
    depends_on:
      - postgres

  processing-service:
    build: ./processing-service
    environment:
      DATABASE_URL: postgresql+asyncpg://weather:weather@postgres:5432/weather_middleware
      PROCESSING_SCHEMA: processing
      INGESTION_SERVICE_URL: http://ingestion-service:8000
      PROCESSING_INTERVAL_SECONDS: 300
      LOG_LEVEL: DEBUG
    ports:
      - "8001:8001"
    depends_on:
      - ingestion-service
```

### Getting Started

```bash
# 1. Clone the repository
git clone <repo-url> && cd weather-middleware-platform

# 2. Start all services
docker compose up --build

# 3. Run ingestion-service migrations
docker compose exec ingestion-service alembic upgrade head

# 4. Run processing-service migrations
docker compose exec processing-service alembic upgrade head

# 5. Verify health
curl http://localhost:8000/health
curl http://localhost:8001/health

# 6. Register a location
curl -X POST http://localhost:8000/api/v1/locations \
  -H "Content-Type: application/json" \
  -d '{"name": "Miami, FL", "latitude": 25.7617, "longitude": -80.1918, "timezone": "America/New_York"}'

# 7. Manually trigger ingestion
curl -X POST http://localhost:8000/api/v1/observations/ingest

# 8. Manually trigger processing
curl -X POST http://localhost:8001/api/v1/process
```

### Alembic Workflow

Each service manages its own migrations independently:

```bash
# Generate a new migration for ingestion-service
docker compose exec ingestion-service alembic revision --autogenerate -m "add weather_code column"

# Apply migrations
docker compose exec ingestion-service alembic upgrade head

# Rollback one migration
docker compose exec ingestion-service alembic downgrade -1
```

Migrations run against a specific PostgreSQL schema. Each service's `env.py` configures `target_metadata` and sets `search_path` to its own schema. This prevents one service's Alembic from detecting or interfering with another service's tables.

### Testing

```bash
# Unit tests (no database required)
docker compose exec ingestion-service pytest tests/unit -v

# Integration tests (requires running database)
docker compose exec ingestion-service pytest tests/integration -v
```

Unit tests use in-memory repository fakes. Integration tests use a separate test schema or a transactional rollback strategy to avoid polluting the development database.

---

## 11. Future Improvements

These are intentionally out of scope for the initial implementation. They are listed to show architectural awareness and to document natural evolution paths.

| Improvement                | What It Would Change                                                                                          | Why Deferred                                                    |
| -------------------------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| **Event-driven processing**| Replace HTTP polling with SQS or EventBridge. ingestion-service publishes an event after each batch; processing-service subscribes. | Adds infrastructure complexity. HTTP polling is sufficient for learning and demonstrates the simpler pattern first. |
| **Redis caching**          | Cache frequently queried processed observations and alerts. Reduce database load for read-heavy endpoints.    | No read performance problem exists yet. Adding a cache before profiling violates YAGNI.                           |
| **API Gateway**            | Place an API Gateway (Kong, AWS API Gateway) in front of both services for auth, rate limiting, and routing.  | Adds a component that is orthogonal to the core learning goals. Can be layered on without refactoring services.   |
| **CI/CD pipeline**         | GitHub Actions: lint, test, build Docker images, push to ECR, deploy to ECS via CDK.                         | Planned as a second phase. The infrastructure supports it (ECR exists, CDK handles deploys).                      |
| **Observability**          | Structured logging (JSON), distributed tracing (OpenTelemetry), Prometheus metrics, Grafana dashboards.       | stdout logging + CloudWatch is sufficient for MVP. OpenTelemetry can be instrumented incrementally.               |
| **Authentication**         | API key or JWT-based authentication on all endpoints.                                                        | Not required for a portfolio demo. The architecture is ready for it (middleware layer in FastAPI).                 |
| **Horizontal scaling**     | Multiple Fargate tasks per service behind the ALB with auto-scaling policies.                                 | Single task is sufficient for expected load. The stateless design means scaling is a configuration change, not a code change. |

---

## 12. Trade-offs

### HTTP Polling vs. Event-Driven Communication

| Dimension        | HTTP Polling (chosen)                            | Event-Driven (SQS/EventBridge)                     |
| ---------------- | ------------------------------------------------ | --------------------------------------------------- |
| Complexity       | Low. Standard request/response. Easy to debug.   | Higher. Requires message broker, DLQs, idempotency. |
| Latency          | Bounded by poll interval (minutes).              | Near real-time (seconds).                            |
| Coupling         | Temporal coupling: processing-service must call ingestion-service synchronously. | Loose coupling: producer and consumer are decoupled. |
| Failure handling | Retry logic in the HTTP client. Straightforward. | Retry policies, visibility timeouts, poison pills.  |
| Observability    | HTTP access logs. Familiar.                       | Requires queue depth monitoring, DLQ alarms.        |

**Decision.** HTTP polling wins because the latency requirement (minutes) does not justify the operational cost of a message broker. The system processes weather data, not financial transactions. A 5-minute processing delay is acceptable. The architecture can evolve to event-driven by replacing the HTTP call with a message publish, leaving the processing-service's domain logic untouched -- exactly the benefit of Clean Architecture.

### Shared Database vs. Separate Databases

| Dimension           | Shared DB / Separate Schemas (chosen)            | Separate Databases                                |
| ------------------- | ------------------------------------------------ | ------------------------------------------------- |
| Operational cost    | One Aurora cluster. One connection string.        | Two Aurora clusters. Double the cost.             |
| Data isolation      | Schema-level. Services cannot accidentally join across schemas (enforced by ORM config). | Full physical isolation.                |
| Transactions        | Cross-schema transactions are technically possible (we explicitly avoid them). | Impossible. Requires saga/compensation. |
| Migration risk      | Alembic configurations must be carefully scoped.  | No interference possible.                         |
| Schema evolution    | Independent within each schema.                  | Fully independent.                                |

**Decision.** Separate schemas in one cluster. The data volumes and team size (one developer) do not justify the operational overhead of two database instances. Schema-level isolation is enforced by giving each service's database user `USAGE` privileges only on its own schema. The ORM is configured to target a single schema, preventing accidental cross-schema access in application code.

### Public Subnets (Fargate) vs. Private Subnets + NAT Gateway

| Dimension           | Public Subnets (chosen)                          | Private Subnets + NAT                            |
| ------------------- | ------------------------------------------------ | ------------------------------------------------- |
| Cost                | $0 additional.                                   | ~$64/month (2 NAT Gateways for HA).              |
| Security posture    | Tasks have public IPs. Mitigated by SG rules.    | Tasks have no public IPs. Defense in depth.       |
| Internet access     | Direct.                                          | Via NAT Gateway.                                  |
| Production-readiness| Not recommended for production workloads.        | Industry standard.                                |

**Decision.** Public subnets for this project. The security groups restrict all inbound traffic to the ALB's security group on specific ports. The database is in private subnets regardless. For a portfolio project, saving $64/month matters. The document explicitly flags this as a trade-off, demonstrating awareness of the production pattern.

### Monorepo vs. Polyrepo

| Dimension            | Monorepo (chosen)                                | Polyrepo                                          |
| -------------------- | ------------------------------------------------ | ------------------------------------------------- |
| Developer experience | Single clone. Shared tooling. Atomic commits.    | Independent repos. Independent CI.               |
| Code sharing         | Shared packages/modules possible.                | Requires publishing internal packages.            |
| CI complexity        | Needs path-based filtering or build targets.     | Each repo has its own pipeline.                   |
| Deployment coupling  | Must be disciplined about independent deployability. | Natural isolation.                            |

**Decision.** Monorepo. With two services and one developer, the overhead of managing multiple repositories (multiple PRs, multiple CI pipelines, cross-repo dependency management) outweighs the isolation benefits. The services are in separate top-level directories with independent `requirements.txt` and `Dockerfile` files, preserving deployability.

---

## 13. Glossary

| Term                     | Definition                                                                                              |
| ------------------------ | ------------------------------------------------------------------------------------------------------- |
| **Raw Observation**      | An unmodified weather data point as received from Open-Meteo. Stored immutably in the ingestion schema. |
| **Processed Observation**| A raw observation enriched with derived metrics (heat index, wind chill, feels-like) and a severity score. |
| **Alert**                | A notification generated when a processed observation breaches a configured threshold.                   |
| **Processing Rule**      | A configurable threshold definition (metric, operator, value, severity) stored in the database.          |
| **Severity Score**       | An integer from 0 (benign) to 10 (extreme) summarizing the overall danger level of an observation.      |
| **Heat Index**           | A derived temperature that accounts for humidity. Relevant when temperature > 27 C and humidity > 40%.   |
| **Wind Chill**           | A derived temperature that accounts for wind speed. Relevant when temperature < 10 C and wind > 4.8 km/h. |
| **WMO Weather Code**     | A standardized integer code describing weather conditions (0 = clear, 95 = thunderstorm, etc.).          |
| **Ingestion Cycle**      | One execution of the scheduled job that polls Open-Meteo for all active locations.                       |
| **Processing Cycle**     | One execution of the scheduled job that fetches unprocessed observations and applies business rules.     |
| **Watermark**            | A timestamp or ID marking the boundary between processed and unprocessed observations.                   |
| **Adapter**              | An infrastructure component that implements a domain protocol (e.g., the Open-Meteo HTTP client).       |
| **Composition Root**     | The module (`dependencies.py`) where all dependencies are wired together for injection.                  |
| **Schema (database)**    | A PostgreSQL namespace that groups related tables. Each service owns one schema.                         |
| **Fargate Task**         | An ECS unit of execution. Each task runs one container (one service) without managing EC2 instances.      |
| **CDK Construct**        | A reusable infrastructure building block in AWS CDK.                                                     |

---

### Data Flow Summary

```mermaid
flowchart LR
    A["Open-Meteo API"] -->|"JSON weather data"| B["ingestion-service"]
    B -->|"raw observations"| C[("PostgreSQL\ningestion schema")]
    D["processing-service"] -->|"GET /api/v1/observations"| B
    D -->|"apply rules + compute metrics"| D
    D -->|"processed observations\n+ alerts"| E[("PostgreSQL\nprocessing schema")]
    F["API Consumer"] -->|"query raw data"| B
    F -->|"query processed data\n+ alerts"| D
```
