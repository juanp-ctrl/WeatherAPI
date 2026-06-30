# ADR 0005: PostgreSQL as the Primary Database

## Status

Accepted

## Context

The Weather Middleware Platform needs a persistent data store for locations, raw observations, processed observations, alerts, and processing rules. The data is relational in nature: observations belong to locations, alerts belong to processed observations, and processing rules are independent entities referenced by alerts. The system requires strong consistency (an observation must be persisted before it can be processed), schema enforcement (data integrity for numeric thresholds and foreign key relationships), and support for complex queries (filtering by time range, location, severity, acknowledgment status).

In production (AWS), the database must support the async PostgreSQL driver (`asyncpg`) used by SQLAlchemy 2. Locally, the database must run in Docker with zero external dependencies. The two services need logical data isolation (separate schemas) within a single database cluster to avoid the operational overhead of running two database instances.

## Decision

We will use **PostgreSQL** as the primary database for the entire platform. In production, the database runs on **Aurora PostgreSQL Serverless v2**. Locally, it runs as a standard `postgres:16` Docker container via Docker Compose.

Both services share a single PostgreSQL cluster but use separate schemas (`ingestion` and `processing`). Each service's database user has `USAGE` privileges only on its own schema, enforcing logical isolation at the database level. This provides the data boundary benefits of separate databases without the cost and operational overhead of two Aurora clusters.

## Alternatives Considered

### Amazon DynamoDB

DynamoDB is a fully managed NoSQL database with automatic scaling, single-digit millisecond latency, and no server management. It would eliminate the need for an Aurora cluster and its associated cost. However, the platform's data model is inherently relational: observations reference locations via foreign keys, alerts reference processed observations and rules, and queries require filtering by multiple dimensions (time range, location, severity). DynamoDB's single-table design pattern would require denormalization and careful access pattern planning, making the schema harder to evolve. DynamoDB also does not support the SQL-based migrations (Alembic) that are a core learning objective. Complex ad-hoc queries (e.g., "all high-severity alerts for a location in the last 24 hours") would require Global Secondary Indexes or be pushed to application code.

### MongoDB

MongoDB offers a flexible document model that could accommodate the JSON-like weather observation data without upfront schema definition. This flexibility is appealing for rapid prototyping. However, the platform benefits from schema enforcement: numeric fields (temperature, humidity, thresholds) must be validated, foreign key relationships ensure referential integrity, and CHECK constraints enforce domain rules (e.g., severity score between 0 and 10). MongoDB's lack of native schema enforcement would push these validations entirely to application code, increasing the risk of data inconsistency. MongoDB also does not integrate with Alembic, and the SQLAlchemy 2 async ecosystem is built around relational databases.

### SQLite

SQLite would be the simplest option for local development: no separate database process, zero configuration, file-based storage. However, SQLite does not support concurrent writes from multiple processes (the two services would contend on a single file lock), does not support schema-level namespace isolation, and cannot run on Aurora in production. Using SQLite locally and PostgreSQL in production would violate the 12-Factor App principle of dev/prod parity and could mask SQL dialect differences during development.

## Consequences

- All persistent state is stored in PostgreSQL, maintaining a single database technology across the stack.
- Both services use SQLAlchemy 2 with the `asyncpg` driver, providing native async I/O aligned with FastAPI.
- Alembic manages schema migrations independently per service, each scoped to its own PostgreSQL schema.
- In production, Aurora PostgreSQL Serverless v2 provides automatic scaling and high availability without managing EC2 instances.
- Locally, a single `postgres:16` container serves both services, started with `docker compose up`.
- The database is placed in private subnets in AWS, accessible only from the ECS security group.

## Pros

- Strong relational model with foreign keys, constraints, and transactions ensures data integrity.
- Mature async driver (`asyncpg`) with proven performance in high-concurrency Python applications.
- Schema-level isolation (`ingestion`, `processing`) provides logical data boundaries without operational overhead.
- Alembic integration enables versioned, repeatable schema migrations.
- Dev/prod parity: the same database engine runs locally (Docker) and in production (Aurora).
- Rich query capabilities for complex filtering, aggregation, and time-range queries.

## Cons

- Aurora PostgreSQL Serverless v2 has a minimum cost even when idle, which is a consideration for a portfolio project.
- PostgreSQL requires a running database process, unlike embedded databases (SQLite).
- Schema management across two services sharing one cluster requires disciplined Alembic configuration to avoid cross-schema interference.
- Vertical scaling limits exist for a single PostgreSQL cluster, though they are far beyond this project's data volumes.

## References

- [Architecture Overview -- Section 5: High-Level Architecture](../architecture/overview.md#5-high-level-architecture)
- [Architecture Overview -- Section 8: Data Model Overview](../architecture/overview.md#8-data-model-overview)
- [Architecture Overview -- Section 12: Shared Database vs. Separate Databases Trade-off](../architecture/overview.md#12-trade-offs)
- [Aurora PostgreSQL Serverless v2 documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html)
