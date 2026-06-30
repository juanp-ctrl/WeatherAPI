# ADR 0004: REST Communication Instead of Messaging Between Services

## Status

Accepted

## Context

The processing-service needs to obtain raw observations from the ingestion-service to apply business rules and generate alerts. This inter-service communication is the primary integration point in the system. The communication pattern must handle the fact that new observations arrive periodically (every 15 minutes from the ingestion scheduler) and that processing can tolerate delays of several minutes without business impact -- weather observations are informational, not transactional.

The choice of communication pattern affects system complexity, operational overhead, coupling between services, failure handling, and observability. The project is developed and operated by a single developer, so operational simplicity is a significant consideration.

## Decision

We will use **synchronous REST over HTTP** for inter-service communication. The processing-service runs a background scheduler that periodically polls the ingestion-service's REST API (`GET /api/v1/observations?status=unprocessed`) to fetch new raw observations. This is a pull-based model where the consumer controls the pace of consumption.

The processing-service calls the ingestion-service through the Application Load Balancer's DNS name (in AWS) or the Docker Compose service name (locally), decoupling service discovery from individual task/container lifecycle.

## Alternatives Considered

### Amazon SQS (Message Queue)

An event-driven pattern where the ingestion-service publishes a message to an SQS queue after persisting each batch of observations, and the processing-service consumes from the queue. This would provide loose temporal coupling (the services do not need to be running simultaneously), built-in retry with dead-letter queues, and near-real-time processing. However, SQS introduces an additional AWS service to provision and monitor, requires idempotent consumers (message deduplication), adds dead-letter queue management, and requires queue depth monitoring. The latency benefit (seconds vs. minutes) is unnecessary for weather data processing. The operational complexity is disproportionate to the value gained for a single-developer project.

### Amazon EventBridge

EventBridge would provide an event bus pattern where the ingestion-service emits events and the processing-service subscribes to them via rules. This offers richer routing capabilities than SQS (content-based filtering, fan-out to multiple consumers) and a fully serverless model. However, EventBridge adds even more infrastructure complexity than SQS: event schemas, rules, targets, and IAM policies. The fan-out capability is unnecessary when there is a single consumer. The event schema registry adds a maintenance surface without clear benefit at this scale.

### gRPC

gRPC would provide strongly typed service contracts via Protocol Buffers, efficient binary serialization, and bidirectional streaming. It is well-suited for high-throughput, low-latency inter-service communication. However, gRPC introduces Protocol Buffer compilation, code generation, and a steeper learning curve for a project whose primary framework (FastAPI) is REST-native. The data volumes are low (dozens of observations per cycle), so binary serialization efficiency is irrelevant. REST is universally understood by portfolio reviewers, whereas gRPC requires additional context.

## Consequences

- The processing-service has a direct HTTP dependency on the ingestion-service. If the ingestion-service is down, the processing-service cannot fetch new observations (though it continues serving already-processed data).
- Inter-service communication is observable through standard HTTP access logs and response codes.
- The polling interval (`PROCESSING_INTERVAL_SECONDS`, default 300 seconds) introduces a bounded delay between ingestion and processing.
- The inter-service API is **paginated** (`limit=100` per request). The processing-service loops through pages until it receives an empty response, preventing memory exhaustion after extended downtime where thousands of observations may have accumulated.
- Retry logic for failed HTTP calls is implemented in the processing-service's HTTP client (httpx with configurable retries, exponential backoff, and timeouts).
- The architecture can evolve to event-driven by replacing the HTTP poll with a message publish, without changing the processing-service's domain logic -- a direct benefit of Clean Architecture.

## Pros

- Simple to implement, debug, and operate. Standard request/response semantics with familiar HTTP status codes.
- No additional infrastructure components (no message broker, no queue, no event bus).
- Observable with standard tools: HTTP logs, response times, status codes.
- The Docker Compose and ALB service names handle service discovery without additional configuration.
- Easy to test end-to-end: a `curl` command can simulate inter-service communication.

## Cons

- Temporal coupling: the processing-service must call the ingestion-service synchronously, creating a runtime dependency.
- Polling introduces bounded latency. New observations are not processed until the next poll cycle.
- If the ingestion-service is slow or unresponsive, the processing-service's scheduler blocks until the HTTP timeout expires.
- No built-in retry/dead-letter semantics. Retry logic must be implemented in application code.

## References

- [Architecture Overview -- Section 7: Request Lifecycle](../architecture/overview.md#7-request-lifecycle)
- [Architecture Overview -- Section 12: HTTP Polling vs. Event-Driven Trade-off](../architecture/overview.md#12-trade-offs)
- [Architecture Overview -- Section 11: Event-Driven Processing (Future)](../architecture/overview.md#11-future-improvements)
