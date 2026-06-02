# Questions — Create a skill for auto-triaging

**Ticket:** INFRA-2059
**Generated:** 2026-06-02T14:30:00Z
**Status:** draft

## Data Flow

- Q1: What data sources feed the existing auto-triager script, and what is the structure of alert payloads received from the #alerts-daytime channel?
   **Target:** The auto-triager script and any alert ingestion module

- Q2: How does the auto-triager currently decide which alerts warrant a response versus being silently dropped or logged only?
   **Target:** The auto-triager's decision logic module and its filtering/prioritization code

- Q3: What outputs does the current auto-triager produce, and how are those outputs delivered back to #alerts-daytime or other downstream consumers?
   **Target:** The auto-triager's output/rendering module and any channel-messaging library it uses

## API Surface

- Q4: What external APIs or services (e.g., monitoring systems, ticketing platforms, notification services) does the existing auto-triager call to gather context for triage decisions?
   **Target:** The auto-triager's integration layer and any service-client modules

- Q5: How is the current auto-triager script invoked — via CLI arguments, stdin/stdout, cron/schedule, or event hooks — and what are its accepted input parameters?
   **Target:** The auto-triager entry point file and its invocation wrapper

## State Management

- Q6: Does the current auto-triager persist any state between runs (e.g., deduplication keys, last-seen alerts, throttle windows), and if so, where is that state stored?
   **Target:** The auto-triager's state persistence module or any shared cache/queue it uses

## Edge Cases

- Q7: How does the existing auto-triager handle malformed, duplicate, or already-resolved alerts, and what failure modes have been observed in production?
   **Target:** The auto-triager's error-handling and retry logic

- Q8: What happens when the auto-triager's response to #alerts-daytime is delivered but the receiving service (e.g., Slack) returns an error or timeout — is there dead-letter handling or retry?
   **Target:** The auto-triager's messaging adapter and any queue/dlq system

## Testing

- Q9: What existing test coverage exists for the auto-triager script, and what mocking or fixture infrastructure is available for testing channel interactions?
   **Target:** The auto-triager's test directory and any shared test utilities in the codebase

- Q10: Which components of the auto-triager are pure functions (testable without external dependencies) versus which require live service connections, and how should that distinction guide test strategy for the new skill?
   **Target:** The auto-triager module architecture and its dependency graph

## Observability

- Q11: What logging, metrics, or tracing does the current auto-triager emit today, and are there any dashboards or alerting rules tied to its behavior that need to be preserved or updated when the skill is extended?
   **Target:** The auto-triager's observability integration (logging module, metric exports, tracer configuration)

- Q12: How can we ensure the new extended skill produces distinguishable log entries from the current version so that a rollback or A/B comparison is feasible after deployment?
   **Target:** The auto-triager's logging configuration and any structured-log schemas it uses
