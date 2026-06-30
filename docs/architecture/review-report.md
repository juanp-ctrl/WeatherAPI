# Architecture Review Board -- Review Report

**Project:** Weather Middleware Platform
**Review Date:** 2026-06-30
**Scope:** All documents under `docs/` (architecture overview + 10 ADRs)
**Reviewers:** Architecture Review Board (ARB)

---

## Executive Summary

The Weather Middleware Platform documentation demonstrates strong architectural thinking: Clean Architecture, explicit trade-off analysis, well-structured ADRs, and a clear mapping from enterprise middleware concepts to a weather domain. The documentation-first approach (no implementation code exists yet) makes this review particularly valuable -- findings can be addressed before they become embedded in code.

However, the review identified **3 Critical**, **6 High**, **14 Medium**, and **8 Low** findings across data integrity, security, scalability, operational readiness, cost awareness, and inter-document consistency. The most urgent issues involve data deduplication, undefined tracking mechanisms, unbounded data growth, and missing security controls on write endpoints.

---

## Findings Summary

| Severity | Count | Immediate Action Required |
|----------|-------|---------------------------|
| Critical | 3     | Yes -- must resolve before implementation |
| High     | 6     | Yes -- should resolve before implementation |
| Medium   | 14    | Address during implementation |
| Low      | 8     | Backlog |

---

## Critical Findings

### C-1: No Idempotency Guard on Ingestion -- Duplicate Observations

**Source:** `overview.md` Section 7 (Ingestion Flow), Section 8 (Data Model)
**Category:** Data Integrity, Hidden Assumption
**Severity:** Critical

**Finding:** The ingestion scheduler fires every 15 minutes and inserts `RawObservation` rows. If the scheduler fires twice for the same window (process restart, clock skew, ECS task replacement during deployment), duplicate observations are inserted. The `raw_observations` table has no UNIQUE constraint on `(location_id, observed_at)` or any deduplication mechanism.

**Hidden Assumption:** The scheduler will fire exactly once per interval, and no external actor will call `POST /api/v1/observations/ingest` during an automatic cycle.

**Impact:** Duplicate raw observations cascade into duplicate processed observations and duplicate alerts. The processing-service would generate spurious alerts for the same weather event.

**Proposed Fix:** Add a UNIQUE constraint on `(location_id, observed_at)` to `raw_observations`. Use `INSERT ... ON CONFLICT DO NOTHING` (or `DO UPDATE` if re-ingestion should refresh data). Document the idempotency guarantee in the data model section.

**Status:** APPLIED to `overview.md`

---

### C-2: Cascading FK Contradicts Immutability Requirement

**Source:** `overview.md` Section 8 (raw_observations table), Section 6 (Key Design Decisions)
**Category:** Inconsistency, Data Integrity
**Severity:** Critical

**Finding:** The `raw_observations` table defines `location_id` as `FK -> locations.id` with a "Cascading reference" note. If this means `ON DELETE CASCADE`, then deleting a location would cascade-delete all its raw observations -- directly contradicting the stated immutability guarantee: "Raw observations are immutable. Once inserted, they are never updated or deleted."

The locations table supports soft-delete via `is_active`, but the cascading FK provides a hard-delete path that violates the audit trail requirement borrowed from laboratory middleware.

**Impact:** Accidental or intentional location deletion would destroy the audit trail, violating the core design principle.

**Proposed Fix:** Change the FK to `ON DELETE RESTRICT` (prevent deletion if observations exist) or `ON DELETE SET NULL` (preserve observations with a null location). Given soft-delete is already supported, `ON DELETE RESTRICT` is the correct choice -- locations with observations cannot be hard-deleted.

**Status:** APPLIED to `overview.md`

---

### C-3: No Authentication on Write Endpoints

**Source:** `overview.md` Section 6 (Endpoints), Section 11 (Future Improvements)
**Category:** Security
**Severity:** Critical

**Finding:** Both services expose write endpoints with zero authentication:
- `POST /api/v1/locations` -- anyone can register locations
- `POST /api/v1/observations/ingest` -- anyone can trigger ingestion cycles
- `POST /api/v1/rules` -- anyone can create processing rules with arbitrary thresholds
- `PATCH /api/v1/alerts/{id}/acknowledge` -- anyone can acknowledge critical alerts
- `DELETE /api/v1/locations/{id}` -- anyone can delete locations
- `POST /api/v1/process` -- anyone can trigger processing cycles

Authentication is listed as "future" in Section 11, but the risk profile of these endpoints (especially rule creation and alert acknowledgment) warrants at minimum an API key gate before any deployment, including demo environments.

**Hidden Assumption:** The system will only be accessed by trusted actors.

**Impact:** In any non-localhost deployment, an unauthenticated actor can manipulate rules (suppress critical alerts by raising thresholds), acknowledge alerts (hide dangerous conditions), or flood the system with locations triggering excessive Open-Meteo calls.

**Proposed Fix:** Add a "Security Boundaries" section to the architecture overview. At minimum, require an API key (via `X-API-Key` header) for all write endpoints. This is a single FastAPI middleware that can be implemented in under an hour. Document this as a pre-deployment requirement, not a future improvement.

**Status:** APPLIED to `overview.md`

---

## High Findings

### H-1: Watermark Mechanism Undefined and Inconsistent

**Source:** `overview.md` Section 7 (Processing Flow), Section 13 (Glossary)
**Category:** Missing Design Detail, Inconsistency
**Severity:** High

**Finding:** The processing-service must distinguish "unprocessed" from "processed" observations. The document uses two contradictory approaches:
- Section 7: `GET /api/v1/observations?status=unprocessed` (implies a status column on raw_observations)
- Section 7 narrative: "using a query parameter or a watermark timestamp" (hedging)
- Glossary: Defines "Watermark" as "A timestamp or ID marking the boundary"

The `raw_observations` table has no `status` column. The `processed_observations` table has a `raw_observation_id` UNIQUE constraint that could be used for an anti-join, but this approach is not described.

**Impact:** Without a concrete mechanism, the two services cannot be implemented consistently. This will become a source of bugs when implementation begins.

**Proposed Fix:** Commit to one approach. The anti-join pattern (find raw observations whose ID does not exist in processed_observations) is the cleanest and requires no schema changes. Document it explicitly. Remove the ambiguous "status=unprocessed" parameter.

**Status:** APPLIED to `overview.md`

**Missing ADR:** This is a significant architectural decision that deserves its own ADR. See recommendation R-1.

---

### H-2: No Data Retention or Purging Strategy

**Source:** `overview.md` Section 8 (Data Model)
**Category:** Scalability Risk, AWS Cost Implication
**Severity:** High

**Finding:** Raw observations are immutable and never deleted. With a 15-minute interval and, say, 10 locations, the system generates ~35,000 rows/month in `raw_observations` alone. Processed observations and alerts add to this. Over a year, the ingestion schema alone accumulates ~420,000 rows with no archival or purging mechanism.

While this volume is manageable for PostgreSQL, the architecture document establishes immutability as a principle without discussing its long-term implications: index bloat, backup size growth, Aurora storage costs ($0.10/GB/month), and query performance degradation on time-range scans.

**Hidden Assumption:** Data volumes will remain small forever.

**Proposed Fix:** Add a "Data Lifecycle" subsection to Section 8 documenting retention policy, table partitioning strategy (by month on `observed_at`), and future archival path (S3 export for cold storage).

**Status:** APPLIED to `overview.md`

---

### H-3: No Pagination on Inter-Service API

**Source:** `overview.md` Section 7, ADR 0004
**Category:** Scalability Risk
**Severity:** High

**Finding:** The processing-service fetches unprocessed observations via `GET /api/v1/observations?status=unprocessed` with no pagination. After extended downtime (ingestion running, processing down), this could return thousands of observations in a single response, causing:
- Memory pressure on both services (serializing/deserializing large JSON arrays)
- HTTP timeout if response exceeds the processing-service's timeout
- Potential ALB request size limits (default 1MB)

**Proposed Fix:** Define pagination on the inter-service API: `?limit=100&offset=0` or cursor-based pagination. The processing-service should loop through pages until exhausted.

**Status:** APPLIED to `overview.md` and `ADR 0004`

---

### H-4: Missing AWS Cost Estimate

**Source:** `overview.md` Section 9
**Category:** AWS Cost Implication
**Severity:** High

**Finding:** The document discusses cost trade-offs for NAT Gateway ($64/month) but never provides a total cost estimate for the production deployment. The actual monthly cost is significantly higher than a portfolio reviewer might expect:

| Resource | Estimated Monthly Cost |
|----------|----------------------|
| Aurora Serverless v2 (0.5 ACU min) | ~$43 |
| ALB | ~$16 + LCU |
| Fargate (2 tasks, 0.25 vCPU, 0.5 GB) | ~$15 |
| ECR storage | ~$1 |
| CloudWatch Logs | ~$2 |
| **Total** | **~$77+/month** |

For a portfolio project, this is a significant ongoing cost that should be documented, along with a "how to tear down" instruction.

**Proposed Fix:** Add a cost estimate table and a teardown command (`cdk destroy`) to the deployment section.

**Status:** APPLIED to `overview.md`

---

### H-5: No Connection Pooling Strategy

**Source:** `overview.md` Section 5, ADR 0002, ADR 0005
**Category:** Scalability Risk, Operational Risk
**Severity:** High

**Finding:** Two services share one Aurora cluster. asyncpg creates connection pools by default, but the configuration is undocumented:
- Default asyncpg pool size is 10 connections per service = 20 total
- Aurora Serverless v2 at 0.5 ACU supports ~45 connections
- If horizontal scaling is enabled (Section 11), 4 tasks x 10 connections = 40, approaching the limit
- No mention of PgBouncer or RDS Proxy for connection multiplexing

**Impact:** Connection exhaustion during scaling events causes cascading failures.

**Proposed Fix:** Document connection pool sizing in the environment configuration table. Add `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW` as configurable environment variables. Mention RDS Proxy as a future scaling path.

**Status:** APPLIED to `overview.md`

---

### H-6: Missing ADR for Unprocessed Observation Tracking

**Category:** Missing ADR
**Severity:** High

**Finding:** How the processing-service identifies unprocessed observations is a fundamental architectural decision with multiple valid approaches (status column, watermark timestamp, anti-join pattern). This decision affects both schemas, the inter-service API contract, and processing correctness. It has no ADR.

**Proposed Fix:** Create ADR 0011 documenting the anti-join approach, alternatives considered (status column, watermark timestamp), and consequences.

**Status:** APPLIED as `docs/adr/0011-anti-join-for-unprocessed-tracking.md`

---

## Medium Findings

### M-1: NFR-6 Claims "Circuit-Breaker-Ready" But No Design Exists

**Source:** `overview.md` Section 3 (NFR-6), Section 6, Section 7
**Category:** Inconsistency, Operational Risk
**Severity:** Medium

**Finding:** NFR-6 states the system "tolerates Open-Meteo downtime gracefully (retries, circuit-breaker-ready design)." No circuit breaker pattern is described anywhere -- not in the overview, not in the ingestion-service design, and not in any ADR. The ingestion flow diagram shows a simple sequential loop with no error handling branches.

**Proposed Fix:** Either implement a circuit breaker (using `tenacity` or a custom state machine) and document it, or downgrade NFR-6 to "retries with exponential backoff" and remove the circuit-breaker claim. Add error handling to the ingestion flow sequence diagram.

---

### M-2: Shallow Health Check Risks Traffic to Unhealthy Tasks

**Source:** `overview.md` Section 6 (Endpoints)
**Category:** Operational Risk
**Severity:** Medium

**Finding:** The `/health` endpoint is described as a "Liveness check" with no details. If it returns 200 without checking database connectivity, the ALB will route traffic to tasks that cannot serve requests (e.g., database connection lost). Kubernetes distinguishes liveness (is the process alive?) from readiness (can it serve traffic?). ECS/ALB health checks serve both purposes.

**Proposed Fix:** Define health check depth: the `/health` endpoint should verify database connectivity (e.g., `SELECT 1`) and return a structured response with component status. Document the health check contract.

---

### M-3: No Rate Limiting on Public Endpoints

**Source:** `overview.md` Section 6
**Category:** Security
**Severity:** Medium

**Finding:** No rate limiting is described for any endpoint. Even with API key authentication (C-3), an authenticated client can flood the system with requests.

**Proposed Fix:** Document rate limiting as a pre-deployment requirement. FastAPI middleware (e.g., `slowapi`) or ALB-level rate limiting via WAF.

---

### M-4: In-Process Scheduler Has No Missed-Cycle Recovery

**Source:** `overview.md` Section 6, Section 7
**Category:** Operational Risk
**Severity:** Medium

**Finding:** The ingestion and processing schedulers run as asyncio background tasks inside the FastAPI process. If the process restarts (deployment, crash, OOM kill), scheduled cycles are missed with no recovery mechanism. There is no "catch up" logic to process the gap.

**Proposed Fix:** Document that the scheduler records the last successful cycle timestamp (e.g., in the database or as a simple file/env). On startup, if the gap exceeds the interval, immediately trigger a catch-up cycle.

**Missing ADR:** The in-process scheduler approach (vs. external scheduler like EventBridge, cron, Celery Beat) is a significant decision with no ADR.

---

### M-5: No Error Handling for Partial Ingestion Failures

**Source:** `overview.md` Section 7 (Ingestion Flow)
**Category:** Missing Design Detail
**Severity:** Medium

**Finding:** The ingestion flow diagram shows a sequential loop over locations. If Open-Meteo returns an error for location 3 of 10, does the cycle:
- (a) Abort entirely, losing locations 4-10?
- (b) Skip location 3 and continue?
- (c) Retry location 3 before moving on?

None of these behaviors are specified.

**Proposed Fix:** Document the error handling strategy: continue on failure with per-location error logging, retry failed locations at the end of the cycle, and include failure counts in the cycle summary log.

---

### M-6: `DATABASE_URL` Contains Plaintext Credentials in Env Var

**Source:** `overview.md` Section 9 (Environment Configuration)
**Category:** Security
**Severity:** Medium

**Finding:** The production configuration injects `DATABASE_URL` containing the full connection string (`postgresql+asyncpg://user:pass@host/db`). Even though credentials come from Secrets Manager, the assembled URL with embedded credentials is visible in the ECS task definition metadata and CloudWatch container logs (if the app logs the URL on startup, which many ORMs do by default).

**Proposed Fix:** Inject database credentials as separate secrets (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`) and construct the URL in application code. This prevents the password from appearing in task definition metadata.

---

### M-7: No Backup or Disaster Recovery Strategy

**Source:** `overview.md` Section 9
**Category:** Operational Risk
**Severity:** Medium

**Finding:** Aurora PostgreSQL is mentioned but there is no discussion of:
- Backup retention period
- Point-in-time recovery (PITR)
- Multi-AZ configuration
- RTO/RPO targets
- Restore procedure

**Proposed Fix:** Document Aurora's default backup retention (1 day), set it to 7 days via CDK, and document the restore procedure.

---

### M-8: No API Versioning Strategy Beyond v1

**Source:** `overview.md` Section 6
**Category:** Future Migration Issue
**Severity:** Medium

**Finding:** All endpoints use `/api/v1/...` but there is no strategy for how `v2` would coexist with `v1`, how the inter-service contract evolves (does processing-service pin to `v1`?), or what constitutes a breaking change.

**Proposed Fix:** Document that the inter-service contract is versioned independently from the public API. Define what constitutes a breaking change (field removal, type change) vs. non-breaking (field addition).

---

### M-9: Missing Network/Security Group Diagram

**Source:** `overview.md` Section 9
**Category:** Missing Diagram
**Severity:** Medium

**Finding:** The deployment diagram shows components but not security boundaries. There is no diagram showing:
- Which security groups exist
- Which ingress/egress rules apply
- Which ports are open between which components
- Internet-facing vs. internal-only paths

**Proposed Fix:** Add a security group diagram showing the three security groups (ALB SG, ECS SG, Aurora SG) and their rules.

---

### M-10: Aurora Serverless v2 ACU Range Not Specified

**Source:** `overview.md` Section 9
**Category:** AWS Cost Implication, Missing Design Detail
**Severity:** Medium

**Finding:** Aurora Serverless v2 requires min/max ACU configuration. The minimum (0.5 ACU) determines the idle cost. The maximum determines burst capacity. Neither is specified. If the CDK code defaults to a high max ACU, an unexpected traffic spike could generate a surprise bill.

**Proposed Fix:** Document ACU range in the CDK stack structure table: min 0.5 ACU, max 2 ACU for a portfolio project.

---

### M-11: No Structured Logging Format Specified

**Source:** `overview.md` Section 4, Section 11
**Category:** Operational Risk
**Severity:** Medium

**Finding:** Section 4 says "Logs are written to stdout" (12-Factor) and Section 11 lists "Structured logging (JSON)" as a future improvement. However, unstructured logs to CloudWatch are difficult to query, filter, and alert on. CloudWatch Logs Insights works dramatically better with JSON-structured logs.

**Proposed Fix:** Use JSON logging from day one (Python's `structlog` or `python-json-logger`). This is a small upfront cost with significant operational payoff.

---

### M-12: No Discussion of Alembic Migration Strategy for Production

**Source:** `overview.md` Section 10
**Category:** Operational Risk
**Severity:** Medium

**Finding:** Alembic migrations are described for local development (`docker compose exec ... alembic upgrade head`) but there is no production migration strategy:
- When do migrations run relative to deployments?
- Are they run as a pre-deployment step, an init container, or a separate ECS task?
- How are migration failures handled?
- How is migration locking managed with multiple Fargate tasks?

**Proposed Fix:** Document that migrations run as a one-shot ECS task before service deployment. Only one migration task runs at a time (ensured by the CDK deployment pipeline).

---

### M-13: `message_template` Allows Arbitrary Template Injection

**Source:** `overview.md` Section 8 (processing_rules table)
**Category:** Security
**Severity:** Medium

**Finding:** The `message_template` column uses `{value}` and `{threshold}` placeholders. If Python's `str.format()` is used for interpolation, a malicious rule creator could inject format strings like `{value.__class__.__init__.__globals__}` to access internal Python objects, potentially leaking sensitive data.

**Proposed Fix:** Use a safe templating mechanism (e.g., `string.Template` with `safe_substitute()` or explicit `str.replace()`) instead of `str.format()`. Validate templates on creation to allow only `{value}` and `{threshold}`.

---

### M-14: Processing Rules Have No Validation Beyond DB Constraints

**Source:** `overview.md` Section 8 (processing_rules table)
**Category:** Data Integrity
**Severity:** Medium

**Finding:** The `metric` field accepts any VARCHAR(64) value. A rule referencing a non-existent metric (e.g., `"barometric_pressure"`) would be accepted by the database but silently fail at evaluation time. The `operator` field accepts any VARCHAR(4), not just the documented operators.

**Proposed Fix:** Add a CHECK constraint on `operator` (`CHECK (operator IN ('>', '>=', '<', '<=', '=='))`). Validate `metric` against a known set of field names at the application layer. Document the valid metric names.

---

## Low Findings

### L-1: ADR 0003 Overstates Processing as "CPU-Bound"

**Source:** ADR 0003
**Category:** Hidden Assumption
**Severity:** Low

**Finding:** ADR 0003 claims "The processing function is CPU-bound (rule evaluation, metric computation)." The actual processing is trivial arithmetic: heat index formula, wind chill formula, threshold comparison. This is not meaningfully CPU-bound.

**Impact:** Minimal. The two-service split is justified by learning objectives regardless.

---

### L-2: N+1 Query Pattern in Processing Flow

**Source:** `overview.md` Section 7 (Processing Flow diagram)
**Category:** Performance
**Severity:** Low

**Finding:** The processing sequence diagram shows `SELECT active rules` inside the per-observation loop. Rules change infrequently. Loading them N times per cycle wastes database round-trips.

**Proposed Fix:** Load rules once at the start of each processing cycle, outside the loop.

---

### L-3: Cross-Schema Logical FK Has No Integrity Guarantee

**Source:** `overview.md` Section 8 (processed_observations)
**Category:** Hidden Assumption
**Severity:** Low

**Finding:** `processed_observations.raw_observation_id` is a "Logical FK to ingestion.raw_observations; not enforced across schemas." This relies on the application-level immutability guarantee. If a future developer adds a hard-delete endpoint for raw observations (violating immutability), processed observations become orphaned.

**Impact:** Low given that immutability is a core principle, but the risk should be documented.

---

### L-4: Missing Per-Service Component Diagrams

**Source:** `overview.md` Section 6
**Category:** Missing Diagram
**Severity:** Low

**Finding:** The directory structure is listed but no C4 Component diagram shows the internal layer dependencies (interface -> application -> domain, infrastructure -> domain).

---

### L-5: No `.gitignore` Documented

**Source:** Project root
**Category:** Missing Configuration
**Severity:** Low

**Finding:** The repository has no `.gitignore`. When implementation begins, Python bytecode, virtual environments, `.env` files, and IDE settings will pollute the repo.

---

### L-6: Docker Compose `depends_on` Only Checks Container Start

**Source:** `overview.md` Section 10
**Category:** Hidden Assumption
**Severity:** Low

**Finding:** `depends_on: - postgres` ensures the container starts but does not wait for PostgreSQL to accept connections. The ingestion-service may crash on startup with "connection refused." Docker Compose v2 supports `depends_on: postgres: condition: service_healthy` with a healthcheck.

**Proposed Fix:** Add a health check to the PostgreSQL service definition and use `condition: service_healthy`.

---

### L-7: No Discussion of Time Synchronization

**Source:** `overview.md` Section 8
**Category:** Hidden Assumption
**Severity:** Low

**Finding:** `observed_at` comes from Open-Meteo and `ingested_at` comes from the server clock. If the Fargate task's clock drifts (unlikely but possible), the gap between these timestamps could produce misleading audit records.

---

### L-8: ADR 0001 States FastAPI is "Relatively Young"

**Source:** ADR 0001
**Category:** Outdated Claim
**Severity:** Low

**Finding:** ADR 0001 lists as a con that "FastAPI is a relatively young framework compared to Flask and Django; its long-term maintenance trajectory... is less proven." FastAPI was released in 2018 and is now one of the most-used Python frameworks. This concern is increasingly dated.

---

## Missing ADRs

| Recommended ADR | Topic | Priority |
|-----------------|-------|----------|
| ADR 0011 | Anti-join pattern for unprocessed observation tracking | High |
| ADR 0012 | In-process asyncio scheduler vs. external scheduler | Medium |
| ADR 0013 | Security model -- API key authentication for write endpoints | Medium |
| ADR 0014 | Data retention and partitioning strategy | Medium |
| ADR 0015 | Alert notification mechanism (store-only vs. push) | Low |

---

## Missing Diagrams

| Diagram | Purpose | Priority |
|---------|---------|----------|
| Security group / network flow diagram | Show ingress/egress rules between ALB, ECS, Aurora | Medium |
| Per-service C4 Component diagram | Show internal layer dependencies | Low |
| Error handling flow (ingestion) | Show retry, skip, and partial failure paths | Medium |

---

## Inter-Document Inconsistencies

| ID | Document A | Document B | Inconsistency |
|----|-----------|-----------|---------------|
| I-1 | `overview.md` Section 7 (`?status=unprocessed`) | `overview.md` Section 8 (no status column) | API parameter references a field that does not exist in the schema |
| I-2 | `overview.md` Section 6 ("Cascading reference") | `overview.md` Section 6 ("Raw observations are immutable") | Cascade delete contradicts immutability |
| I-3 | `overview.md` NFR-6 ("circuit-breaker-ready") | `overview.md` Section 7 (no error handling in flow) | Claimed capability not designed |
| I-4 | ADR 0003 ("CPU-bound processing") | `overview.md` Section 7 (trivial arithmetic) | Overstated workload characterization |

---

## Summary of Applied Changes

The following Critical and High findings were applied directly to the documentation:

1. **C-1 (APPLIED):** Added UNIQUE constraint and idempotency note to `raw_observations` schema
2. **C-2 (APPLIED):** Changed cascading FK to `ON DELETE RESTRICT` with explanation
3. **C-3 (APPLIED):** Added Security Boundaries section to architecture overview
4. **H-1 (APPLIED):** Defined anti-join watermark mechanism concretely in processing flow
5. **H-2 (APPLIED):** Added Data Lifecycle subsection with retention strategy
6. **H-3 (APPLIED):** Added pagination to inter-service API contract
7. **H-4 (APPLIED):** Added AWS cost estimate and teardown instructions
8. **H-5 (APPLIED):** Added connection pooling configuration to environment table
9. **H-6 (APPLIED):** Created ADR 0011 for unprocessed observation tracking

---

*End of Architecture Review Report*
