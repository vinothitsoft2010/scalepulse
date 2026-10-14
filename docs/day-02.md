# Day 2: Requirements

## Study focus

DDIA Chapter 1 introduces reliability, scalability, and maintainability as goals for data-intensive systems. Functional requirements say what the service does; non-functional requirements describe qualities and constraints.

## ScalePulse rate-limit feature

Functional requirements:

- Identify a caller with a provisioned API key; never use its raw secret as a storage key.
- Apply the key's configured request limit and time window.
- Allow requests within the limit; reject excess requests with HTTP 429 and a positive `Retry-After`.
- Share decisions across gateway workers through Redis.
- Keep a stable error response and test the boundary at limit N and request N+1.

Non-functional requirements:

- Measure limiter-added p50/p95/p99 against the Day 1 baseline.
- State whether capacity is per instance or aggregate, and characterize key count and request mix.
- Do not log API secrets or request bodies.
- Choose and document dependency failure behavior. This implementation fails closed when Redis is required but unavailable.

The selected algorithm is an exact sliding-window log: each allowed request is a sorted-set member; an atomic Lua script prunes expired events, checks the count, and records the request. Rejected requests are not stored. Redis is the shared clock/counter authority.

## Study prompts

1. Classify “return 429 after N requests” and “p99 latency under X” as functional or non-functional.
2. Why is 100,000 RPS a scenario, not a capacity requirement until scope and workload are specified?
