# Day 5: Hardware Metrics

- **CPU:** high utilization with flat throughput suggests CPU saturation or contention. Compare total and per-process use as workers change.
- **IOPS:** storage operations per second. The Day 1 in-memory endpoint performs no per-request database writes, so its RPS does not measure storage IOPS.
- **Network bandwidth:** approximate payload bandwidth as request rate times average request-plus-response bytes, then multiply bytes/s by 8 for bits/s. Include protocol overhead for production estimates.
- **Reproducibility:** record CPU/RAM, VM limits, software versions, worker count, Locust process count, request mix, and duration.

The benchmark is not enough to declare a hardware bottleneck. Add the relevant workload and collect host/container metrics before drawing that conclusion.

## Study prompt

At 20,000 RPS and 800 average bytes per request plus response, estimate payload bandwidth before protocol overhead.
