"""Measure peak memory for node-state tables of different sizes and log it for the team.

    python -m kairos_repro.tools.memcheck                      # compacted: 1,000,000 nodes x 100 dims
    python -m kairos_repro.tools.memcheck --authors-size       # also the reference code's 5,045,000 x 200

Everyone runs it on their own machine and commits the new line in results/env_report.txt.
This allocates and touches the state table only, so it is a LOWER BOUND on the model's
footprint. Once the model exists, extend it to build the real TGN memory and run 20 batches.
"""
import argparse
import datetime
import getpass
import os
import platform
import resource
import sys
from typing import List, Tuple

import numpy as np

from kairos_repro import common as c


def peak_rss_gb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return (r if sys.platform == "darwin" else r * 1024) / 1e9


def total_ram_gb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().total / 1e9
    except ImportError:
        return float("nan")


def touch_table(nodes: int, dim: int) -> float:
    table = np.zeros((nodes, dim), dtype=np.float32)
    table += 1.0  # force every page to be resident
    gb = table.nbytes / 1e9
    del table
    return gb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authors-size", action="store_true")
    a = ap.parse_args()
    cases: List[Tuple[str, int, int]] = [("compacted", 1_000_000, 100)]
    if a.authors_size:
        cases.append(("authors_5045000x200", 5_045_000, 200))
    c.RESULTS.mkdir(exist_ok=True)
    line_fmt = "%s | %s | %s | ram=%.1fGB | %s | %s | table=%.2fGB | peak_rss=%.2fGB"
    for label, nodes, dim in cases:
        gb = touch_table(nodes, dim)
        line = line_fmt % (datetime.date.today(), getpass.getuser(), platform.processor() or platform.machine(),
                           total_ram_gb(), platform.platform(), label, gb, peak_rss_gb())
        print(line)
        with open(c.RESULTS / "env_report.txt", "a") as fh:
            fh.write(line + "\n")


if __name__ == "__main__":
    main()
