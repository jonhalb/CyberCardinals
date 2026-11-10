"""Training entry point. OWNER: Jonas (story M3-02).

    python -m kairos_repro.model.train --config configs/paper_faithful.json --seed 0 [--quick]

Contract (so make, the tests and the clean-checkout script can rely on it):
- trains on common.TRAIN_IDS merged and time-ordered, no shuffling
- seeds everything with common.seed_everything(seed)
- writes results/<config name>/model_seed{N}.pt (git-ignored) and train_log_seed{N}.csv (committed)
- --quick shortens training for the live demo; the real run's time is recorded in results/env_report.txt
"""
import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--quick", action="store_true")
    ap.parse_args()
    raise NotImplementedError("story M3-02: training loop")


if __name__ == "__main__":
    main()
