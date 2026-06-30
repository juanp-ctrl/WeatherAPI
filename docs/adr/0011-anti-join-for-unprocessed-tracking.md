# ADR 0011: Anti-Join Pattern for Unprocessed Observation Tracking

## Status

Accepted

## Context

The processing-service must identify which raw observations have not yet been processed. This is the primary coordination mechanism between the two services: the ingestion-service persists raw observations, and the processing-service must discover new ones on each polling cycle.

The mechanism must be correct (never skip an observation), efficient (not degrade as the observation table grows), and simple (avoid adding coordination state that could become inconsistent). It must also work across the service boundary -- the processing-service communicates with the ingestion-service via REST, not direct database access.

Three approaches were considered, each with different trade-offs in schema coupling, query complexity, and failure modes.

## Decision

We will use a **high-water mark timestamp** combined with a **processed-ID anti-join** to identify unprocessed observations.

The processing-service tracks the `ingested_at` timestamp of the most recently processed observation as its **high-water mark**. On each polling cycle, it requests observations from the ingestion-service with `ingested_at` greater than its high-water mark, paginated in batches of 100. The ingestion-service serves this query using the existing `ix_raw_observations_ingested_at` index.

As a correctness safeguard, the processing-service also checks the `UNIQUE` constraint on `processed_observations.raw_observation_id` before inserting. If a raw observation has already been processed (e.g., due to a retry after partial failure), the insert is rejected, preventing duplicate processing.

The high-water mark is persisted in the processing-service's database (a simple `processing.watermarks` table with a single row per source) so it survives process restarts. On first startup with no watermark, the processing-service fetches all unprocessed observations from the beginning.

## Alternatives Considered

### Status Column on raw_observations

Adding a `status` column (`unprocessed`, `processing`, `processed`) to the `raw_observations` table would make unprocessed observations directly queryable. However, this approach has significant drawbacks:

- It requires the processing-service to **write back** to the ingestion schema, violating the schema ownership boundary (ingestion-service owns the `ingestion` schema).
- It introduces a two-phase update pattern: fetch observation, process it, update status. If the processing-service crashes between processing and status update, the observation is stuck in `processing` and requires manual intervention or a timeout-based recovery.
- It adds write contention on the `raw_observations` table, which is designed to be append-only and immutable.

### Full Anti-Join (No Watermark)

The processing-service could query the ingestion-service for all raw observation IDs, then locally compute the set difference against all `raw_observation_id` values in `processed_observations`. This is correct but does not scale: as the observation tables grow, transferring and comparing full ID sets becomes expensive. A time-bounded approach (high-water mark) avoids this by narrowing the query window.

### Event-Driven Notification

The ingestion-service could emit an event (via SQS, EventBridge, or webhook) after persisting each batch of observations. The processing-service would consume these events, eliminating the need for any tracking mechanism. This is the most architecturally clean approach but was deferred for the same reasons documented in ADR 0004: the operational complexity of a message broker is disproportionate to the project's current scale and learning objectives.

## Consequences

- The processing-service maintains a `watermarks` table in the `processing` schema with a `last_ingested_at` timestamp.
- The ingestion-service exposes a `since` query parameter on `GET /api/v1/observations` that filters by `ingested_at > :since`.
- The inter-service API response is paginated (`limit=100`). The processing-service loops through pages until it receives an empty page.
- On first startup or watermark reset, the processing-service processes all historical observations (bounded by pagination).
- The `UNIQUE` constraint on `processed_observations.raw_observation_id` provides a last-resort idempotency guarantee.
- No writes to the `ingestion` schema are required from the processing-service, preserving schema ownership boundaries.

## Pros

- Preserves the immutability of `raw_observations` -- no status column, no writes from external services.
- Respects schema ownership: only the ingestion-service writes to the `ingestion` schema.
- Efficient: the watermark narrows queries to a small time window, leveraging the existing `ingested_at` index.
- Resilient to restarts: the watermark is persisted and survives process replacement.
- Idempotent: the UNIQUE constraint on `raw_observation_id` prevents duplicate processing.

## Cons

- The watermark introduces a small piece of coordination state that must be managed (persisted, initialized on first run, reset-able for reprocessing).
- Clock skew between the ingestion-service and the database could cause observations to be missed if `ingested_at` is set by the application rather than the database (`DEFAULT now()` mitigates this).
- If the ingestion-service re-ingests an observation (due to idempotent upsert) without changing `ingested_at`, the processing-service will not re-process it. This is the desired behavior for immutable data but could be surprising if re-processing is intended.

## References

- [Architecture Overview -- Section 7: Request Lifecycle](../architecture/overview.md#7-request-lifecycle)
- [Architecture Overview -- Section 8: Data Model Overview](../architecture/overview.md#8-data-model-overview)
- [ADR 0004 -- REST Communication](0004-rest-communication-instead-of-messaging.md)
