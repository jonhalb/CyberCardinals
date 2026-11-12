"""Paper vs ours, one table, three columns: what the paper reported, what we got, the difference.

    python -m kairos_repro.eval.compare --run results/paper_faithful --seed 0 --name "Paper-faithful (ours)"

Reads  <run>/graph_scores_seed{seed}.csv  (test splits only are scored)
Writes <run>/metrics_seed{seed}.json and <run>/comparison_seed{seed}.md
"""
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

from kairos_repro.common import PAPER_SOURCE, PAPER_TABLE4
from kairos_repro.eval.metrics import summarize
from kairos_repro.eval.scores_io import read_scores

ORDER = ["TP", "TN", "FP", "FN", "precision", "recall", "accuracy", "auc"]


def metrics_from_rows(rows: List[Dict]) -> Dict[str, float]:
    test = [r for r in rows if r["split"].startswith("test")]
    if not test:
        raise ValueError("no test rows in score file")
    return summarize([r["label"] for r in test], [r["pred"] for r in test], [r["score"] for r in test])


def comparison_rows(paper: Dict[str, float], ours: Dict[str, float]) -> List[Tuple[str, float, float, float]]:
    return [(m, paper[m], ours[m], ours[m] - paper[m]) for m in ORDER]


def _fmt(metric: str, v: float) -> str:
    return "%d" % v if metric in ("TP", "TN", "FP", "FN") else "%.3f" % v


def to_markdown(rows, name: str) -> str:
    lines = ["| Metric | Paper (%s) | %s | Difference |" % (PAPER_SOURCE, name), "|---|---|---|---|"]
    for m, p, o, d in rows:
        diff = "%+d" % d if m in ("TP", "TN", "FP", "FN") else "%+.3f" % d
        lines.append("| %s | %s | %s | %s |" % (m, _fmt(m, p), _fmt(m, o), diff))
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--name", default="Ours")
    a = ap.parse_args()
    rows = read_scores(a.run / ("graph_scores_seed%d.csv" % a.seed))
    m = metrics_from_rows(rows)
    (a.run / ("metrics_seed%d.json" % a.seed)).write_text(json.dumps(m, indent=2))
    md = to_markdown(comparison_rows(PAPER_TABLE4, m), a.name)
    if "auc_scores" in m:
        md += ("\nAUC above is from the 0/1 predictions, so it depends on the threshold. AUC from the continuous "
               "graph scores (threshold-free): %.3f.\n" % m["auc_scores"])
    (a.run / ("comparison_seed%d.md" % a.seed)).write_text(md)
    print(md)


if __name__ == "__main__":
    main()
