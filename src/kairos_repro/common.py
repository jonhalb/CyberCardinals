"""Experiment definition shared by every script.

Import splits, constants and paths from here. Never retype them: a split that drifts
between scripts is how a reproduction stops being believable.
"""
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
RAW_ARCHIVE = DATA_RAW / "all.tar.gz"
RAW_TSV = DATA_RAW / "all.tsv"
PROCESSED_DIR = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
CONFIGS = ROOT / "configs"
FEATURES_CSV = RESULTS / "graph_features.csv"

# Dataset facts. Verified against the real file on 2026-11-09 (see docs/verification_2026-11-09.md).
DATASET_SHA256 = "1551d7eba96fdea4958b9c0b6c15c773983a5ebdf9f1ffe4430cbb7ea85d23cf"
TOTAL_EDGES = 89_770_902
NUM_GRAPHS = 600

# Type alphabets as single letters (node a-h, edge A-H then i-z), fixed and sorted so the
# one-hot order is identical on every run and every machine.
NODE_TYPES: List[str] = list("abcdefgh")
EDGE_TYPES: List[str] = list("ABCDEFGH") + list("ijklmnopqrstuvwxyz")
MSG_DIM = 2 * len(NODE_TYPES) + len(EDGE_TYPES)  # src type + edge type + dst type = 42

SCENARIOS: Dict[str, int] = {  # name -> first graph id; 100 graphs each
    "youtube": 0, "gmail": 100, "vgame": 200,
    "drive_by_download": 300, "download": 400, "cnn": 500,
}
ATTACK_BASE = 300
BENIGN_BASES = [0, 100, 200, 400, 500]

TRAIN_IDS: List[int] = list(BENIGN_BASES)
VAL_IDS: List[int] = [b + i for b in BENIGN_BASES for i in range(1, 25)]
TEST_BENIGN_IDS: List[int] = [b + i for b in BENIGN_BASES for i in range(25, 100)]
TEST_ATTACK_IDS: List[int] = list(range(ATTACK_BASE, ATTACK_BASE + 100))
TEST_IDS: List[int] = sorted(TEST_BENIGN_IDS + TEST_ATTACK_IDS)

SEEDS = [0, 1, 2, 3, 4]
AUTHORS_SEED = 12345  # torch.manual_seed value in the authors' train.py (confirm against source)

PAPER_SOURCE = "KAIROS (IEEE S&P 2024), Table 4, row 'Manzoor et al.'"
PAPER_TABLE4 = {"TP": 100, "TN": 375, "FP": 0, "FN": 0,
                "precision": 1.0, "recall": 1.0, "accuracy": 1.0, "auc": 1.0}

# Paper Table 3 as printed: (average nodes, average edges). Keys are the paper's own row labels.
PAPER_TABLE3 = {
    "YouTube": (8292, 113229), "Gmail": (6827, 37382), "Video Game": (8831, 310814),
    "Attack": (8891, 28423), "Download": (8637, 112958), "CNN": (8990, 294903),
}
PAPER_LABEL_OF = {"youtube": "YouTube", "gmail": "Gmail", "vgame": "Video Game",
                  "drive_by_download": "Attack", "download": "Download", "cnn": "CNN"}
# Paper Table 2, row 'Manzoor et al.'
PAPER_TABLE2 = {"nodes": 999_999, "edges_millions": 89.8, "attack_edges": 2_842_345, "attack_pct": 3.165}


def label(graph_id: int) -> int:
    """1 = attack, 0 = benign."""
    return int(ATTACK_BASE <= graph_id < ATTACK_BASE + 100)


def split_of(graph_id: int) -> str:
    if graph_id in set(TRAIN_IDS):
        return "train"
    if graph_id in set(VAL_IDS):
        return "val"
    if graph_id in set(TEST_ATTACK_IDS):
        return "test_attack"
    if graph_id in set(TEST_BENIGN_IDS):
        return "test_benign"
    raise ValueError("graph id out of range: %r" % (graph_id,))


def scenario_of(graph_id: int) -> str:
    name = None
    for key, base in SCENARIOS.items():
        if graph_id >= base:
            name = key
    if name is None or not 0 <= graph_id < NUM_GRAPHS:
        raise ValueError("graph id out of range: %r" % (graph_id,))
    return name


def graph_path(graph_id: int) -> Path:
    return PROCESSED_DIR / ("graph_%d.npz" % graph_id)


def load_config(name: str) -> dict:
    with open(CONFIGS / (name + ".json")) as fh:
        return json.load(fh)


def seed_everything(seed: int) -> None:
    """Seed python, numpy and torch. PYTHONHASHSEED must be set before Python starts:
    the Makefile exports it, and the value is recorded in every results file."""
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch
        torch.manual_seed(seed)
    except ImportError:
        pass
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
