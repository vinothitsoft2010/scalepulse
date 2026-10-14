# Day 6: Latency, Throughput, and Spikes

Latency is the duration of an individual request; throughput is completed requests per unit time. Report both with errors and tail percentiles. High throughput does not mean the service is healthy if p99 or errors are rising.

Locust's current users are closed-loop: each waits for a response before sending another request. Little's Law is $L = \lambda W$: average in-flight requests equal throughput times average latency. Closed-loop load can fall as the service slows, hiding overload (coordinated omission). A flash-sale test should also use fixed-arrival-rate/open-loop traffic and observe p95/p99, 429/5xx rates, and recovery.

## Study prompts

1. Why can p99 be important even when average latency is low?
2. How does a fixed arrival rate differ from the current Locust test?
