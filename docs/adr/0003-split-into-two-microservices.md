# ADR 0003: Split the System into Two Microservices

## Status

Accepted

## Context

The Weather Middleware Platform performs two distinct functions: (1) acquiring and normalizing raw weather data from an external provider, and (2) applying business rules, computing derived metrics, and generating alerts from that raw data. These two functions have different change cadences, failure modes, and scaling characteristics. The ingestion function depends on an external API (Open-Meteo) and is sensitive to network issues and upstream rate limits. The processing function is CPU-bound (rule evaluation, metric computation) and depends only on internal data.

The project also has explicit learning objectives: practicing microservice decomposition, inter-service REST communication, independent deployability, and container orchestration on ECS Fargate. The architectural decision must balance these educational goals with the practical overhead of operating multiple services.

## Decision

We will decompose the system into **two microservices**: `ingestion-service` and `processing-service`.

The `ingestion-service` owns data acquisition -- polling Open-Meteo, normalizing responses, and persisting raw observations. It is the system of record for raw weather data. The `processing-service` owns data enrichment -- consuming raw observations via REST, applying configurable business rules, computing derived metrics, and generating alerts. Each service has its own codebase directory, `Dockerfile`, `requirements.txt`, Alembic migrations, and PostgreSQL schema.

This separation enforces a clear data ownership boundary: the processing-service never calls Open-Meteo directly. All weather data flows through the ingestion-service, establishing a single source of truth for raw observations.

## Alternatives Considered

### Monolith

A single application containing both ingestion and processing logic would be simpler to develop, deploy, and debug. There would be no inter-service communication overhead, no network serialization, and a single deployment artifact. However, a monolith would not exercise microservice patterns (service decomposition, REST inter-service calls, independent schema management, per-service deployment) which are core learning objectives of the project. The monolith also couples the ingestion and processing failure domains: a bug in rule evaluation could crash the ingestion scheduler, causing data loss from missed Open-Meteo polls.

### Three or More Microservices

A finer-grained decomposition -- for example, separating the scheduler, the Open-Meteo adapter, and the rule engine into distinct services -- would push microservice principles further. However, this level of decomposition introduces significant operational overhead for a single-developer project: more Docker images, more ECS task definitions, more inter-service calls, and more failure surfaces. The two-service split already achieves the learning objectives (independent deployability, REST communication, schema isolation) without the diminishing returns of further decomposition. The architecture can be refined later if the system grows.

### Modular Monolith

A modular monolith would keep both functions in a single deployable unit but enforce strict module boundaries (separate packages, no cross-module imports except through defined interfaces). This approach captures some benefits of microservices (logical separation, independent evolution of modules) without the network overhead. However, it does not exercise container-based deployment, inter-service HTTP communication, or independent schema management with Alembic -- all of which are explicit learning objectives.

## Consequences

- Two independent services are built, tested, and deployed separately, each with its own `Dockerfile` and CI pipeline (future).
- Inter-service communication uses REST over HTTP. The processing-service polls the ingestion-service's API for unprocessed observations.
- Each service owns a separate PostgreSQL schema (`ingestion`, `processing`) within the same database cluster.
- Alembic migrations are managed independently per service, scoped to the respective schema.
- A failure in one service does not directly crash the other, though the processing-service degrades when the ingestion-service is unavailable.

## Pros

- Clear separation of concerns: ingestion owns data acquisition, processing owns data enrichment.
- Independent deployability allows updating business rules in the processing-service without redeploying the ingestion-service.
- Fault isolation: an Open-Meteo outage affects ingestion but does not prevent the processing-service from serving already-processed data.
- Exercises real-world microservice patterns: service decomposition, REST communication, independent schema management, and container orchestration.
- Each service can be scaled independently based on its workload profile (I/O-bound vs. CPU-bound).

## Cons

- Network overhead: inter-service REST calls add latency and introduce a failure surface that a monolith does not have.
- Operational complexity: two Docker images, two sets of migrations, two health check endpoints, two log streams.
- Data consistency: there is no cross-service transaction. The processing-service uses eventual consistency through polling.
- Development overhead for a single developer: changes that span both services require coordinating two codebases.

## References

- [Architecture Overview -- Section 5: High-Level Architecture](../architecture/overview.md#5-high-level-architecture)
- [Architecture Overview -- Section 6: Service Responsibilities](../architecture/overview.md#6-service-responsibilities)
- [Architecture Overview -- Section 12: Monorepo vs. Polyrepo Trade-off](../architecture/overview.md#12-trade-offs)
