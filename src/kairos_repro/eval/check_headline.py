"""Print the headline comparison for a finished run and fail loudly if it is missing.

    python -m kairos_repro.eval.check_headline --run results/paper_faithful --seed 0

Used by scripts/clean_checkout_test.sh so a clean clone proves it can produce the number.
"""
import argparse
import json
import sys
from pathlib import Path

from kairos_repro.common import PAPER_TABLE4
from kairos_repro.eval.compare import comparison_rows, to_markdown


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    path = a.run / ("metrics_seed%d.json" % a.seed)
    if not path.exists():
        print("MISSING %s: the pipeline did not produce a headline number" % path)
        return 1
    m = json.loads(path.read_text())
    print(to_markdown(comparison_rows(PAPER_TABLE4, m), "Ours"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
