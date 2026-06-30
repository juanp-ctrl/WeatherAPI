# ADR 0001: Use FastAPI as the Web Framework

## Status

Accepted

## Context

The Weather Middleware Platform requires a Python web framework to expose REST APIs for two microservices (ingestion-service and processing-service). The framework must support asynchronous request handling because both services perform I/O-bound operations: the ingestion-service polls the Open-Meteo API over HTTP, and both services interact with PostgreSQL via async drivers (`asyncpg`). The system also needs background task scheduling (periodic ingestion and processing cycles), dependency injection for wiring repositories and use cases, and automatic OpenAPI documentation to support portfolio reviewers who want to explore the API without reading source code.

The project has explicit learning objectives: practicing FastAPI, SQLAlchemy 2, and async Python in a realistic distributed system. The framework choice must balance developer productivity, async ecosystem maturity, and alignment with those learning goals.

## Decision

We will use **FastAPI** as the web framework for both microservices.

FastAPI provides native async/await support built on Starlette and Uvicorn, a built-in dependency injection system (`Depends()`) that aligns with the Clean Architecture composition root pattern, and automatic OpenAPI/Swagger documentation generated from Pydantic models. Its dependency injection mechanism allows us to wire repository protocols and use cases at the router level, making the object graph explicit and testable without hidden global state.

## Alternatives Considered

### Flask

Flask is the most widely adopted Python microframework and has a mature ecosystem. However, Flask was designed for synchronous WSGI workloads. Async support was added in Flask 2.0, but it remains an afterthought rather than a core design principle. Flask lacks built-in dependency injection, requiring third-party libraries (e.g., Flask-Injector) that add integration friction. It also does not generate OpenAPI documentation automatically, requiring Flask-RESTx or similar extensions. Given that both services are I/O-bound and async-first, Flask would have required more boilerplate to achieve the same async performance.

### Django REST Framework (DRF)

Django is a batteries-included framework with a mature ORM, admin panel, and authentication. However, Django's ORM is synchronous and would conflict with the project's decision to use SQLAlchemy 2 with `asyncpg`. Django's async support (introduced in 3.1) is still evolving and does not cover the ORM layer fully. DRF adds significant framework surface area (serializers, viewsets, routers) that overlaps with FastAPI's Pydantic-based approach but with more implicit behavior. The project does not need Django's admin panel, template engine, or built-in ORM, making DRF heavier than necessary.

### Litestar (formerly Starlite)

Litestar is a modern async framework that competes directly with FastAPI. It offers similar features: native async, dependency injection, automatic OpenAPI docs, and Pydantic integration. Litestar was considered because it addresses some FastAPI criticisms (e.g., more explicit DI lifecycle management). However, Litestar has a smaller community, fewer production references, and less third-party content (tutorials, Stack Overflow answers). Since the project serves as a portfolio piece, using FastAPI maximizes recognizability for reviewers. The architecture's Clean Architecture approach means a future migration from FastAPI to Litestar would be localized to the interface layer.

## Consequences

- All HTTP routing, request validation, and response serialization are handled by FastAPI across both services.
- Pydantic v2 models serve as the schema layer for request/response validation and OpenAPI documentation.
- The `Depends()` mechanism is the composition root for injecting repositories and use cases into route handlers.
- Background scheduling for ingestion and processing cycles runs inside the FastAPI process using `asyncio`.
- Both services produce interactive Swagger UI documentation at `/docs` with zero additional configuration.

## Pros

- Native async/await support aligned with `asyncpg` and `httpx` for non-blocking I/O.
- Built-in dependency injection eliminates the need for third-party DI containers.
- Automatic OpenAPI documentation makes the API self-describing for portfolio reviewers.
- Large community and extensive documentation reduce onboarding friction and debugging time.
- Pydantic integration provides runtime type validation at API boundaries with minimal boilerplate.

## Cons

- FastAPI's dependency injection is request-scoped by default, requiring care to manage session lifetimes correctly with SQLAlchemy.
- The framework couples route definitions to Pydantic models, which can blur the boundary between interface and application layers if not disciplined.
- FastAPI is a relatively young framework compared to Flask and Django; its long-term maintenance trajectory, while currently strong, is less proven.

## References

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Architecture Overview -- Section 4: Architecture Principles](../architecture/overview.md#4-architecture-principles)
- [Architecture Overview -- Section 3: Learning Objectives](../architecture/overview.md#3-system-goals)
- [Starlette documentation](https://www.starlette.io/)
