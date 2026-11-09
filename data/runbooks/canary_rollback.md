# Canary rollback procedure

## When to rollback

- SLO breach after a canary promotion
- Error budget burn linked to a specific version in deployments catalog
- Latency regression only on canary traffic share

## Steps

1. Confirm version and traffic % via `get_recent_deployments`
2. Set canary traffic to 0% (or full rollback to previous stable)
3. Verify `latency_p99` and `error_rate_503` in SLO snapshot trend toward baseline
4. Open post-incident doc; keep failed version blocked until root-cause review

## Notes

- Do not roll forward without a fix for the regression
- Stable channel should absorb 100% traffic after rollback
