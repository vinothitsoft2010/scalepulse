# Day 3: Reliability, Scalability, and Maintainability

## Concepts

- **Reliability:** correct service under faults, overload, and recovery.
- **Scalability:** sustaining increased load while preserving relevant service qualities.
- **Maintainability:** how safely and quickly people can understand, operate, and change the system.
- **SLI:** a defined measurement, such as successful eligible requests divided by eligible requests.
- **SLO:** a target for an SLI over a time window.
- **SLA:** an externally communicated commitment, often with remedies. ScalePulse has no SLA today.

A 429 is an expected policy decision, not automatically a service failure. Track rate-limited traffic separately from 5xx failures. The draft 99.9% availability SLO remains a proposal, not a commitment; set latency targets after measuring the Redis path.

## Study prompts

1. Why should a correctly rate-limited 429 not count as a 5xx availability failure?
2. What extra obligations turn an internal SLO into an SLA?
