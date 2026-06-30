# ADR 0009: Open-Meteo as the External Weather Data Provider

## Status

Accepted

## Context

The ingestion-service needs a reliable external source of real weather observation data. The platform's architecture mirrors enterprise middleware systems where an external "instrument" produces raw data that the middleware ingests, normalizes, and processes. The choice of weather data provider directly affects development friction (API key management, rate limits, cost), data quality (coverage, accuracy, available variables), and the system's ability to demonstrate realistic data ingestion patterns.

The provider must supply current weather conditions and hourly data for arbitrary coordinate pairs, return data in a machine-readable format (JSON), and support the specific weather variables needed for derived metric calculations (temperature, humidity, wind speed, precipitation, weather codes).

## Decision

We will use the **Open-Meteo API** as the external weather data provider. Open-Meteo provides a free, keyless JSON API that returns current conditions and hourly forecasts for any coordinate pair. The ingestion-service calls the `/v1/forecast` endpoint with latitude, longitude, and desired weather variables (`temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`, `precipitation`, `weather_code`).

The Open-Meteo client is implemented as an **adapter** behind a domain protocol (`WeatherDataSource`). This means the platform is not architecturally coupled to Open-Meteo; swapping to a different provider requires writing a new adapter, not changing business logic or use cases.

## Alternatives Considered

### OpenWeatherMap

OpenWeatherMap is one of the most popular weather APIs with extensive documentation and a large user community. It offers current weather, forecasts, historical data, and weather maps. However, OpenWeatherMap requires an API key even for free-tier access, which introduces credential management (environment variables, secrets), and the free tier has strict rate limits (60 calls/minute, 1,000 calls/day). For a portfolio project where reviewers need to clone and run the system immediately, requiring API key registration creates unnecessary friction. Open-Meteo's keyless access eliminates this barrier entirely.

### WeatherAPI.com

WeatherAPI.com provides a generous free tier (1 million calls/month) with current conditions, forecasts, and historical data. Its JSON responses are well-structured and include many derived fields (heat index, wind chill, feels-like). However, like OpenWeatherMap, it requires API key registration. Additionally, having the provider return pre-calculated derived metrics would undermine the processing-service's purpose -- the project specifically needs raw observations so the processing-service can demonstrate business rule evaluation and derived metric computation as learning objectives.

### National Weather Service (NWS) API

The NWS API is a free, keyless government API that provides weather data for U.S. locations. It requires no authentication and has no rate limits. However, the NWS API has a complex, non-standard JSON-LD response format that requires significant parsing effort, covers only U.S. territory (limiting the generality of the demo), and has documented reliability issues with intermittent downtime. Open-Meteo provides global coverage with a simpler, more predictable JSON response format.

## Consequences

- The ingestion-service depends on Open-Meteo's API availability. Open-Meteo downtime prevents new data acquisition (but does not affect serving existing data).
- No API key management is required, simplifying both local development and production deployment.
- The Open-Meteo adapter normalizes the provider-specific JSON response into canonical `RawObservation` domain entities, isolating the rest of the system from the provider's response format.
- Portfolio reviewers can clone the repository and start ingesting real weather data immediately without registering for any external service.
- The adapter pattern means a future provider switch (e.g., to OpenWeatherMap for production use with richer data) is a localized change.

## Pros

- Free and keyless: zero setup friction for developers and portfolio reviewers.
- No rate limit concerns for a project with low call volumes (a few calls every 15 minutes).
- Global coverage: any coordinate pair returns weather data, enabling flexible demo locations.
- Simple JSON response format that is straightforward to parse and normalize.
- Returns raw weather variables without pre-calculated derived metrics, preserving the processing-service's value proposition.

## Cons

- Open-Meteo is a community project without a commercial SLA, making it unsuitable for production-critical applications.
- Data accuracy may be lower than commercial providers that aggregate multiple data sources.
- The API's response format and available variables could change without notice, though the adapter pattern limits the blast radius of such changes.
- No historical data backfill endpoint in the free tier, limiting testing scenarios that require historical data.

## References

- [Open-Meteo API documentation](https://open-meteo.com/en/docs)
- [Architecture Overview -- Section 1: Project Overview](../architecture/overview.md#1-project-overview)
- [Architecture Overview -- Section 6: ingestion-service Key Design Decisions](../architecture/overview.md#6-service-responsibilities)
- [Architecture Overview -- Section 7: Ingestion Flow](../architecture/overview.md#7-request-lifecycle)
