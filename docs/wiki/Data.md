# Data

**Dataset:** StreamSpot (Manzoor et al., KDD 2016), the dataset behind KAIROS Table 4, row "Manzoor et al.".
600 provenance graphs of system activity: 100 per scenario, five benign (YouTube, Gmail, Video Game, Download, CNN)
and one attack (drive-by download). Each line of the file is one edge.

## How we got it

`make data` (`src/kairos_repro/data/download.py`) downloads `all.tar.gz` from the dataset's own GitHub repository
(`raw.githubusercontent.com/sbustreamspot/sbustreamspot-data/master/all.tar.gz`), **checks its SHA-256 before using it**,
and extracts the single member `all.tsv`. Nothing is copied by hand.

| | Value |
|---|---|
| Archive | `all.tar.gz`, 87,860,166 bytes |
| SHA-256 | `1551d7eba96fdea4958b9c0b6c15c773983a5ebdf9f1ffe4430cbb7ea85d23cf` (matches the team plan; stored in `src/kairos_repro/common.py`) |
| Extracted | `all.tsv`, 2,288,207,702 bytes |
| Verified on | 2026-11-09 (clean 2-core Linux box); 2026-11-12 Jonas and Emiliano (WSL2 Ubuntu 22.04) |

`make graphs` (`src/kairos_repro/data/build_graphs.py`) then streams the file into one compressed array file per graph
(`data/processed/graph_{id}.npz`) plus a `manifest.json`, **without PostgreSQL** (the authors load it into a database
first; see ADR-0002). `make stats` (`src/kairos_repro/data/stats.py`) writes `results/data_report.md`, which every number
below comes from. `tests/test_real_sample.py` re-checks the processed graphs against these numbers on any machine that has the data.

## The four questions

**1. How big is it, and what are the columns?**
89,770,902 edge rows in 600 graphs. Six tab-separated columns: `source-id, source-type, dest-id, dest-type, edge-type, graph-id`.
The graphs sit in the file as 600 contiguous blocks, in graph-id order.

**2. What type is each column?**
Node ids are opaque strings (we keep them as text, then renumber them). The three type columns are single-letter codes:
8 node types (`a`-`h`: process, thread, file, MAP_ANONYMOUS, NA, stdin, stdout, stderr) and 26 edge types
(system calls such as read, write, execve, clone, connect, mmap2). The graph id is an integer 0-599.
**There are no timestamps**: the dataset's preprocessing removed them, so the order of lines in the file is the only time signal.
We use the 1-based line number as `t` (deviation D-04), which is the same ordering the authors use (their serial `_id`).

**3. What is missing or malformed?**
Nothing: 0 malformed lines, 0 unknown node-type codes, 0 unknown edge-type codes, so nothing was dropped or repaired.
`t` runs from 1 to 89,770,902 with no gaps.

**4. What does the thing we predict look like?**
One label per graph: **attack = graphs 300-399** (drive-by download), benign = everything else.

## Class balance and the split

| | Benign graphs | Attack graphs | Attack share |
|---|---|---|---|
| All data | 500 | 100 | 16.7% |
| Train (graphs 0, 100, 200, 400, 500) | 5 | 0 | 0% |
| Validation (x01-x24 of each benign scenario) | 120 | 0 | 0% |
| Test (x25-x99 of each benign scenario + all attacks) | 375 | 100 | 21.1% |

The model only ever sees benign graphs before testing. Guessing "benign" for every test graph already scores
**375/475 = 0.789 accuracy**: that is the do-nothing baseline (see [Baselines](Baselines)).

By edges the attack is much rarer: **2,842,345 attack edges = 3.166%** of all edges, the same count as the paper's Table 2.

## Per-scenario averages vs the paper's Table 3

| Scenario (graph ids) | Avg nodes (ours) | Avg edges (ours) | Paper row with the same numbers |
|---|---|---|---|
| YouTube (0-99) | 8,292 | 113,229 | YouTube |
| Gmail (100-199) | 6,827 | 37,382 | Gmail |
| Video Game (200-299) | 8,637 | 112,958 | **Download** |
| Drive-by download, attack (300-399) | 8,891 | 28,423 | Attack |
| Download (400-499) | 8,831 | 310,814 | **Video Game** |
| CNN (500-599) | 8,990 | 294,903 | CNN |

**Finding: the paper's Table 3 has the Video Game and Download rows swapped.** Four rows match the paper exactly.
Our Video Game graphs match the paper's *Download* numbers and our Download graphs match the paper's *Video Game*
numbers, and the graph-id ranges come from the dataset's own README. It does not change any result: it is a labelling slip in the table.

Also worth noting: **Gmail graphs are the smallest benign graphs** (about 37k edges), closest in size to the attack graphs
(about 28k). In early prototype runs the highest-scoring benign graphs were Gmail graphs, so they are the most likely false positives.

## Nodes: the paper's count vs ours

| Quantity | Ours | Paper Table 2 |
|---|---|---|
| Edges | 89,770,902 | 89.8 M |
| Attack edges | 2,842,345 (3.166%) | 2,842,345 (3.165%) |
| Distinct node ids | **5,044,482** | 999,999 |

The paper's 999,999 looks capped or wrong. Our count is almost exactly the 5,045,000-row node table the authors' code allocates.
Node ids are effectively unique to each graph (no graph has more than 9,284 nodes), so we process one graph at a time and
renumber its nodes 0..n-1. That keeps peak memory around 0.5 GB instead of the authors' 64 GB requirement (ADR-0005, D-13).

## What we found in the authors' loader

The authors insert `all.tsv` into PostgreSQL in batches of 10,000 rows and only insert when a batch is full. The final
partial batch is never written: 89,770,902 = 8,977 x 10,000 + 902, so **their database is missing the last 902 lines
of the file, all from graph 599** (a CNN test graph). Our streaming loader keeps every line. See ADR-0002 and deviation D-20.
