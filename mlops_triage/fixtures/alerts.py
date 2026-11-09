SAMPLE_ALERT = """
[PagerDuty] CRITICAL serving-prod-eu
Model inference latency p99 jumped from 120ms to 4.2s over 15 minutes.
GPU utilization on replica batch-7 stuck at 99%; rest of fleet nominal.
Last deployment: rec-engine v3.8.1 canary 12% traffic, 09:14 UTC.
Error rate 503 on /v1/recommend: 0.1% -> 8.7%. Rollback not yet attempted.
"""

TRAINING_ALERT = """
[W&B] WARNING experiment-train-us
Training job job-4821 loss diverged (NaN) after LR scheduler step 34000.
Last checkpoint saved 12 min ago at step 33800 on s3://ml-artifacts/exp-12/.
GPU memory stable; single-node A100. No automatic rollback configured.
"""
