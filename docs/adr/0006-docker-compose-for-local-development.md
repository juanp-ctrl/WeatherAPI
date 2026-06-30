# ADR 0006: Docker Compose for Local Development

## Status

Accepted

## Context

The platform consists of two microservices and a PostgreSQL database. A developer cloning the repository must be able to start the entire system with minimal setup to evaluate the project, run tests, or contribute. The local development environment must closely mirror the production deployment (ECS Fargate with Aurora PostgreSQL) to catch environment-specific issues early and maintain dev/prod parity as prescribed by the 12-Factor App methodology.

The project targets portfolio reviewers who may spend only a few minutes evaluating the codebase. A "clone and run in under five minutes" experience is a stated goal. This means the local development tooling must have minimal prerequisites and require no manual service configuration.

## Decision

We will use **Docker Compose** to orchestrate the local development environment. A single `docker-compose.yml` file defines all three components: a PostgreSQL 16 container, the ingestion-service, and the processing-service. Running `docker compose up --build` starts the entire platform. The only prerequisites are Docker and Docker Compose.

Each service is built from its own `Dockerfile`, and configuration is injected via environment variables defined in the Compose file. Service names (`postgres`, `ingestion-service`, `processing-service`) serve as DNS hostnames within the Docker network, enabling inter-service communication without hardcoded IPs.

## Alternatives Considered

### Manual Setup (Native Installation)

Developers could install Python, PostgreSQL, and all dependencies directly on their host machine. This approach offers the fastest feedback loop (no container build step) and full IDE integration (debugger, profiler). However, it requires installing and configuring PostgreSQL, managing Python virtual environments, and ensuring version compatibility across operating systems. Differences between macOS, Linux, and Windows PostgreSQL installations can cause subtle bugs. This approach violates the container-first design principle and undermines dev/prod parity. A portfolio reviewer who just wants to see the project run should not have to install PostgreSQL.

### Kubernetes (Minikube / kind)

Running the services on a local Kubernetes cluster would more closely mirror a container orchestration environment. Tools like Minikube or kind can simulate a multi-node cluster on a developer machine. However, Kubernetes adds significant complexity: writing Deployment and Service manifests, configuring networking, managing resource limits, and learning kubectl. The production target is ECS Fargate, not Kubernetes, so the operational knowledge gained from local Kubernetes does not transfer directly. Docker Compose achieves the same goal -- containerized multi-service orchestration -- with dramatically less configuration.

### Podman Compose

Podman is a daemonless container engine that is an alternative to Docker. Podman Compose provides Docker Compose-compatible orchestration. While Podman has advantages (rootless containers, no daemon process), Docker remains the industry standard for local development and is pre-installed or easily installable on all major operating systems. Podman has occasional compatibility gaps with Docker Compose features and a smaller community for troubleshooting. Choosing Docker maximizes the probability that a portfolio reviewer already has the required tooling installed.

## Consequences

- The only local prerequisites are Docker and Docker Compose (both included in Docker Desktop).
- A single command (`docker compose up --build`) starts the database, both services, and the Docker network.
- Environment variables are centrally defined in `docker-compose.yml`, ensuring consistent configuration.
- Alembic migrations run inside the service containers (`docker compose exec <service> alembic upgrade head`), using the same database connection as the running service.
- Tests run inside the service containers, ensuring they execute against the same Python version and dependencies as production.

## Pros

- Near-zero setup friction for portfolio reviewers: clone, `docker compose up`, done.
- Dev/prod parity: services run in containers locally, just as they do on ECS Fargate.
- Reproducible environments: the Dockerfile and Compose file pin all dependencies and runtime configuration.
- Docker Compose networking provides DNS-based service discovery, mirroring the ALB-based routing in production.
- Widely adopted tooling that most developers already have installed.

## Cons

- Container build times add overhead to the development feedback loop, especially for initial builds.
- Debugging inside containers is less ergonomic than native debugging (requires `docker compose exec` or remote debugger configuration).
- Docker Desktop on macOS has known performance overhead for file system mounts, which can slow down development with mounted volumes.
- The Compose file is a separate configuration surface that must be kept in sync with production environment variables.

## References

- [Architecture Overview -- Section 10: Local Development](../architecture/overview.md#10-local-development)
- [Architecture Overview -- Section 4: Container-First Design](../architecture/overview.md#4-architecture-principles)
- [Architecture Overview -- Section 4: 12-Factor App](../architecture/overview.md#4-architecture-principles)
- [Docker Compose documentation](https://docs.docker.com/compose/)
