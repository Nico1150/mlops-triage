# Training: NaN loss divergence

## Symptoms

- Loss becomes NaN mid-run
- LR scheduler recently stepped to a new phase

## Actions

1. Stop job to avoid corrupt checkpoints
2. Resume from last good checkpoint (step before NaN)
3. Lower learning rate or adjust scheduler
4. Inspect batch for bad inputs / extreme labels

Priority is typically P2 unless blocking a production release deadline.
