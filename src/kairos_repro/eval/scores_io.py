"""Per-graph score files: graph_scores_seed{N}.csv with columns graph_id,split,label,score,pred."""
import csv
from pathlib import Path
from typing import Dict, List

FIELDS = ["graph_id", "split", "label", "score", "pred"]


def write_scores(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in FIELDS})


def read_scores(path: Path) -> List[Dict]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["graph_id"] = int(r["graph_id"])
        r["label"] = int(r["label"])
        r["score"] = float(r["score"])
        r["pred"] = int(r["pred"])
    return rows
