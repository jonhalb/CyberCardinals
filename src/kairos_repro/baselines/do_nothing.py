"""Baseline B0: predict benign for every graph. Needs no data, only the split.

    python -m kairos_repro.baselines.do_nothing

This is the score the paper's method has to beat on the same split. On the 375 benign + 100
attack test graphs it gets TP=0 TN=375 FP=0 FN=100, accuracy 375/475.
"""
from typing import Dict, List

from kairos_repro import common as c
from kairos_repro.eval.scores_io import write_scores


def rows() -> List[Dict]:
    ids = c.VAL_IDS + c.TEST_IDS
    return [{"graph_id": g, "split": c.split_of(g), "label": c.label(g), "score": 0.0, "pred": 0} for g in ids]


def main() -> None:
    out = c.RESULTS / "baselines" / "do_nothing"
    write_scores(out / "graph_scores_seed0.csv", rows())
    print("wrote", out / "graph_scores_seed0.csv")


if __name__ == "__main__":
    main()
