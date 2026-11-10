# Runbook

1. Machine: Linux or WSL2 Ubuntu 22.04. `bash scripts/setup_env.sh && conda activate kairos`.
2. `make unit` (tests pass).
3. `make reproduce` (data, graphs, stats, baselines, train, evaluate, compare). Expected time and peak memory: (fill in).
4. Open `results/paper_faithful/comparison_seed0.md`.
5. Seeds: `make seeds`. Ablation: `make variant`.
Tested by someone outside the team on: (date, machine, notes).
