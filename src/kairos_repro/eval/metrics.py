"""Confusion matrix and the paper's metrics. Pure Python so it runs anywhere and is easy to test."""
from typing import Dict, Optional, Sequence


def confusion(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict[str, int]:
    tp = tn = fp = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == 1 and p == 1:
            tp += 1
        elif t == 0 and p == 0:
            tn += 1
        elif t == 0 and p == 1:
            fp += 1
        else:
            fn += 1
    return {"TP": tp, "TN": tn, "FP": fp, "FN": fn}


def _div(a: float, b: float) -> float:
    return a / b if b else 0.0


def auc_from_scores(y_true: Sequence[int], scores: Sequence[float]) -> float:
    """ROC AUC as the Mann-Whitney U statistic with tied scores counted as half."""
    n_pos = sum(1 for t in y_true if t == 1)
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    pairs = sorted(zip(scores, y_true))
    n = len(pairs)
    rank_sum_pos = 0.0
    i = 0
    while i < n:
        j = i
        while j < n and pairs[j][0] == pairs[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0  # ranks i+1 .. j
        for k in range(i, j):
            if pairs[k][1] == 1:
                rank_sum_pos += avg_rank
        i = j
    u = rank_sum_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def summarize(y_true: Sequence[int], y_pred: Sequence[int],
              scores: Optional[Sequence[float]] = None) -> Dict[str, float]:
    """Metrics for one run. 'auc' is computed from the hard 0/1 predictions, which is what the
    authors' evaluation does; 'auc_scores' uses the continuous graph scores when given."""
    c = confusion(y_true, y_pred)
    out: Dict[str, float] = dict(c)
    out["precision"] = _div(c["TP"], c["TP"] + c["FP"])
    out["recall"] = _div(c["TP"], c["TP"] + c["FN"])
    out["accuracy"] = _div(c["TP"] + c["TN"], sum(c.values()))
    p, r = out["precision"], out["recall"]
    out["f1"] = _div(2 * p * r, p + r)
    out["auc"] = auc_from_scores(y_true, list(y_pred))
    if scores is not None:
        out["auc_scores"] = auc_from_scores(y_true, scores)
    return out
