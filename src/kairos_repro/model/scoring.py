"""Graph-level scoring and thresholding, exactly as the paper describes for one window per graph.

Paper Sec. 4.3.1: an edge is anomalous when its reconstruction error exceeds the window mean
plus 1.5 standard deviations. Sec. 4.3.3: a window's score is the mean error of those edges.
With one window per graph (Sec. 5.1.1) the graph score is that window score. The threshold is
set from benign validation data; taking the maximum validation score is the authors' rule.

Choices the paper does not state (logged in docs/deviations.md): population SD (ddof=0), and
the fall-back to the mean error when no edge exceeds the cut (all errors identical).
"""
from typing import Iterable, List, Sequence

import numpy as np


def graph_score(errors: Iterable[float], sd_multiplier: float = 1.5, ddof: int = 0) -> float:
    e = np.asarray(list(errors), dtype=float)
    if e.size == 0:
        raise ValueError("a graph with no edges has no score")
    cut = e.mean() + sd_multiplier * e.std(ddof=ddof)
    high = e[e > cut]
    return float(high.mean()) if high.size else float(e.mean())


def fit_threshold(validation_scores: Sequence[float]) -> float:
    if len(validation_scores) == 0:
        raise ValueError("need validation scores to set a threshold")
    return float(max(validation_scores))


def predict(scores: Sequence[float], threshold: float) -> List[int]:
    """1 = attack. Strictly greater than the threshold, as in the authors' evaluation."""
    return [int(s > threshold) for s in scores]
