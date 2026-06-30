# ADR 0002: Use SQLAlchemy 2 as the ORM

## Status

Accepted

## Context

Both microservices need to interact with PostgreSQL for persisting and querying domain entities (locations, raw observations, processed observations, alerts, processing rules). The data access layer must support async operations to align with FastAPI's async request lifecycle and the `asyncpg` driver. The project follows Clean Architecture, which requires that the domain layer has zero imports from infrastructure frameworks. This means the ORM must support a mapping strategy where domain entities remain plain Python objects, decoupled from ORM-specific base classes.

Additionally, the project needs a migration tool for versioned schema changes. The ORM choice directly affects which migration tools are available and how schema evolution is managed.

## Decision

We will use **SQLAlchemy 2** with the `asyncpg` driver as the ORM for both microservices.

SQLAlchemy 2 introduced native async session support (`AsyncSession`), the unit-of-work pattern for managing transactions, and imperative mapping that allows domain entities to remain framework-free. Its mature ecosystem includes Alembic for versioned migrations, which is essential for managing schema evolution across two independent schemas (`ingestion` and `processing`). SQLAlchemy 2 also supports schema-qualified table names, enabling both services to target separate PostgreSQL schemas within the same database cluster.

## Alternatives Considered

### Raw SQL with asyncpg

Using `asyncpg` directly with raw SQL queries would eliminate the ORM layer entirely, giving full control over query construction and performance. However, this approach pushes the burden of result mapping, transaction management, and migration tracking onto application code. Without an ORM, the repository implementations would need manual row-to-entity mapping, which is tedious and error-prone as the schema grows. There is also no built-in migration tool; we would need to adopt a standalone migration framework (e.g., `yoyo-migrations`) or write migration scripts manually. The unit-of-work pattern would have to be reimplemented from scratch.

### Tortoise ORM

Tortoise ORM is an async-first ORM for Python inspired by Django's ORM. It provides a simpler API than SQLAlchemy and native async support. However, Tortoise uses an active-record pattern where model classes inherit from a framework base class (`Model`). This would couple domain entities to the ORM, violating the Clean Architecture principle of framework-independent domain layers. Tortoise also has a significantly smaller community, fewer production deployments, and its migration tool (Aerich) is less mature than Alembic. Schema-level namespace isolation (separate PostgreSQL schemas per service) is not well supported.

### Django ORM (standalone)

Django's ORM can be used outside of Django with some configuration effort. It is the most battle-tested Python ORM with excellent migration support. However, Django's ORM is fundamentally synchronous. While Django 4.1 introduced async ORM methods, they are wrappers around `sync_to_async` and do not provide true async database I/O. Using Django's ORM would negate the performance benefits of `asyncpg` and introduce a synchronous bottleneck in an otherwise async pipeline. Additionally, running Django's ORM standalone requires bootstrapping Django settings, which adds unnecessary configuration complexity.

## Consequences

- Both services use `AsyncSession` from SQLAlchemy 2 for all database interactions, ensuring non-blocking I/O.
- Domain entities are mapped to database tables using SQLAlchemy's imperative mapping or declarative base, with the mapping configuration isolated in the infrastructure layer.
- Alembic manages all schema migrations independently per service, with each service's `env.py` scoped to its own PostgreSQL schema.
- Repository implementations use SQLAlchemy's query API and are the only code that imports SQLAlchemy, keeping the domain layer ORM-free.
- The unit-of-work pattern manages transaction boundaries at the use-case level.

## Pros

- Native async support via `AsyncSession` and `asyncpg` aligns with FastAPI's async architecture.
- Alembic provides mature, versioned migrations with autogenerate support for detecting schema drift.
- Imperative mapping preserves Clean Architecture by keeping domain entities free of ORM base classes.
- The unit-of-work pattern simplifies transaction management across multiple repository operations.
- Large community, extensive documentation, and widespread adoption reduce risk and debugging time.
- Schema-qualified table names support the separate-schemas-in-one-cluster deployment model.

## Cons

- SQLAlchemy 2's async API is more verbose than simpler ORMs; session lifecycle management requires careful scoping.
- The learning curve is steeper than lightweight alternatives like Tortoise ORM.
- Imperative mapping requires additional configuration compared to the simpler declarative approach.
- Alembic autogenerate can miss certain schema changes (e.g., CHECK constraints, custom types), requiring manual migration scripts.

## References

- [SQLAlchemy 2.0 documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic documentation](https://alembic.sqlalchemy.org/)
- [asyncpg driver](https://github.com/MagicStack/asyncpg)
- [Architecture Overview -- Section 5: High-Level Architecture](../architecture/overview.md#5-high-level-architecture)
- [Architecture Overview -- Section 4: Repository Pattern](../architecture/overview.md#4-architecture-principles)
