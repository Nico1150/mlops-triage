# Serving: latency p99 spike

## Symptoms

- p99 inference latency jumps 10x+ while p50 stays normal
- GPU utilization pinned on one or few replicas
- 503 rate may rise on inference routes

## Likely causes

1. Bad canary deployment (new model version or batch size change)
2. Hot key / traffic skew on specific replicas
3. GPU memory leak on a single pod

## Immediate actions

1. Check last deployment and canary traffic percentage
2. Compare p99 vs error_rate SLO snapshots for the same window
3. If canary correlates with spike: roll back canary to last stable version
4. Drain or restart unhealthy replicas if GPU stuck at 99% without traffic

## Escalation

- P1 if customer-facing SLO breached > 15 minutes
- Page serving on-call and model owner for rec-engine changes
