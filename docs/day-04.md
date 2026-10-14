# Day 4: Scaling

## Baseline interpretation

Day 1 measured 17,557 RPS with one native worker and 39,661 RPS with four. Four workers produced about 2.26x throughput, not 4x. Worker processes use more CPU cores on one host; that is scaling up the host's allocated resources. Adding gateway instances across hosts is scaling out.

Horizontal instances need shared rate-limit state. A per-process counter would give each instance a separate allowance and violate a global per-key limit, so ScalePulse uses Redis as shared state.

Docker Desktop measurements are specific to a macOS VM and must not be generalized to Linux production. The load generator also competes for CPU with the app.

## Study prompts

1. What bottleneck might prevent throughput from scaling linearly with worker count?
2. Why does a distributed gateway require a shared counter store?
