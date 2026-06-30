# ADR 0010: Repository Pattern for Data Access

## Status

Accepted

## Context

Both microservices need to access PostgreSQL for CRUD operations on domain entities (locations, raw observations, processed observations, alerts, processing rules). The project follows Clean Architecture, which mandates that the domain layer has zero dependencies on infrastructure frameworks. This means use cases and domain logic must not import SQLAlchemy, reference database sessions, or construct SQL queries. A data access abstraction is needed to decouple business logic from the persistence mechanism.

The data access pattern must also support testability: use cases should be unit-testable without a running database by substituting the real persistence layer with in-memory fakes. The pattern must work with SQLAlchemy 2's `AsyncSession` for async database operations while keeping the interface framework-agnostic.

## Decision

We will use the **Repository Pattern** to encapsulate all data access. Repository protocols (Python `Protocol` classes or abstract base classes) are defined in the domain layer (e.g., `ObservationRepository`, `AlertRepository`, `LocationRepository`). These protocols declare the data access contract (methods like `save`, `find_by_id`, `find_unprocessed`) without referencing any infrastructure framework.

Concrete implementations live in the infrastructure layer and use SQLAlchemy 2's `AsyncSession` to execute queries. Use cases depend on the repository protocol, not on the implementation. FastAPI's `Depends()` mechanism wires the concrete implementation at the composition root (`dependencies.py`), making the dependency graph explicit and swappable.

## Alternatives Considered

### Active Record Pattern

The Active Record pattern embeds persistence logic directly in domain entities: each entity inherits from an ORM base class and has methods like `save()`, `delete()`, and class methods like `find_by_id()`. Django's ORM and Tortoise ORM use this pattern. Active Record is simpler for small applications because there is no separate repository layer -- the entity *is* the data access mechanism. However, Active Record tightly couples domain entities to the ORM framework, violating Clean Architecture's dependency rule. Entities become untestable without a database connection, and swapping the persistence layer (e.g., replacing PostgreSQL with DynamoDB for a specific table) requires modifying the entity itself. The pattern also makes it tempting to scatter query logic throughout the codebase rather than centralizing it.

### Data Access Objects (DAO)

The DAO pattern is similar to the Repository pattern but typically operates at the table level rather than the aggregate level. A DAO provides CRUD operations mapped directly to database tables, whereas a Repository abstracts over aggregates and can encapsulate complex queries that span multiple tables. For this project, the distinction is subtle because most entities map one-to-one with tables. However, the Repository pattern is more expressive for domain-driven scenarios (e.g., `find_unprocessed_observations()` as a named method rather than a generic `find_by_criteria()`) and integrates more naturally with Clean Architecture's use-case-driven design.

### Direct SQLAlchemy Usage in Use Cases

The simplest approach would be to inject `AsyncSession` directly into use cases and write SQLAlchemy queries inline. This eliminates the repository layer entirely, reducing the number of abstractions. However, this approach couples use cases to SQLAlchemy's API, making them impossible to unit-test without a database (or extensive mocking of the session's internal state). It also scatters SQL construction logic across use cases, making it harder to find and optimize queries. When the schema evolves, every use case that touches the affected tables must be updated, rather than updating a single repository implementation.

## Consequences

- Repository protocols are defined in the domain layer and contain no SQLAlchemy imports.
- SQLAlchemy-based repository implementations live in the infrastructure layer and are the only code that imports SQLAlchemy's query API.
- Use cases are tested with in-memory repository fakes that implement the same protocol, requiring no database or ORM setup.
- Adding a new query pattern requires adding a method to the protocol and implementing it in the repository.
- Swapping the persistence layer for a specific entity (e.g., using Redis for caching processed observations) means writing a new repository implementation, not changing any use case.
- FastAPI's `Depends()` wires repository implementations at the composition root, making the dependency graph visible and testable.

## Pros

- Clean separation between domain logic and persistence, enforcing the Clean Architecture dependency rule.
- Use cases are unit-testable with in-memory fakes, enabling fast test execution without database setup.
- Persistence layer is swappable: PostgreSQL, DynamoDB, Redis, or in-memory implementations can coexist behind the same protocol.
- Query logic is centralized in repository implementations, making it easy to find, optimize, and audit.
- Named repository methods (e.g., `find_unprocessed()`, `find_by_location_and_time_range()`) express domain intent more clearly than raw queries scattered across use cases.

## Cons

- Additional abstraction layer increases the number of files and interfaces, which can feel over-engineered for simple CRUD operations.
- Repository protocols must be kept in sync with their implementations; adding a method requires changes in at least two places (protocol and implementation).
- The pattern can lead to repository interfaces that grow large over time if not carefully managed, accumulating query methods for every access pattern.
- In-memory fakes may not perfectly replicate database behavior (e.g., transaction isolation, constraint enforcement), potentially masking integration issues.

## References

- [Architecture Overview -- Section 4: Repository Pattern](../architecture/overview.md#4-architecture-principles)
- [Architecture Overview -- Section 4: Dependency Injection](../architecture/overview.md#4-architecture-principles)
- [Architecture Overview -- Section 6: Internal Layers](../architecture/overview.md#6-service-responsibilities)
- Martin Fowler, *Patterns of Enterprise Application Architecture* -- Repository pattern
- Robert C. Martin, *Clean Architecture* -- The Dependency Rule
