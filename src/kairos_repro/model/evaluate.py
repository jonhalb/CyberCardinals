"""Score validation and test graphs. OWNER: Aaliyah (story M3-03).

    python -m kairos_repro.model.evaluate --config configs/paper_faithful.json --seed 0

Contract:
- loads results/<config name>/model_seed{N}.pt
- per-edge errors for each graph in VAL_IDS + TEST_IDS -> model.scoring.graph_score
- threshold = fit_threshold(validation scores); pred = predict(scores, threshold)
- writes results/<config name>/graph_scores_seed{N}.csv through eval.scores_io.write_scores
- one pass, deterministic at test time for the cross-entropy decoder
- the authors_variant ablation samples negatives: seed that pass too and record the seed
"""
import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.parse_args()
    raise NotImplementedError("story M3-03: evaluation pass")


if __name__ == "__main__":
    main()
