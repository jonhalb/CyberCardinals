# ADR-0002: Stream all.tsv instead of loading PostgreSQL

Status: **accepted** (evidence collected by Emiliano, story M2-03, 2026-11-12).

The authors load the file into PostgreSQL and read each graph back ordered by a serial `_id`, which they use as time.
all.tsv is already sorted into 600 contiguous graph blocks, so we stream it and use the 1-based line number as t.

## Evidence

Source for the authors' side: `StreamSpot/src/preprocess.py` and `StreamSpot/src/README.md` in github.com/ubc-provenance/kairos
(commit `1090fd1`). Our side: `make graphs` on WSL2 Ubuntu 22.04 (2 min 40 s, peak RSS 0.95 GB), checked by `tests/test_real_sample.py`.

- [x] **Per-graph edge counts match the totals.** `data/processed/manifest.json`: 600 graphs, 89,770,902 edges,
  5,044,482 compacted node ids; the 600 per-graph counts sum to 89,770,902 and match the arrays on disk
  (`test_manifest_totals`, `test_manifest_matches_files`). Attack graphs 300-399 hold 2,842,345 edges, the paper's Table 2 value.
  `rows.iter_graph_blocks` raises if a graph id reappears after its block ends, and it never did: the file is 600 contiguous blocks.
- [x] **Ordering of first and last rows matches the `_id` order.** The authors' table declares `_id serial primary key`
  and `preprocess.py` inserts the lines in file order (`for line in f`, then `execute_values` per batch), so `_id` is
  the line's position in the file, starting at 1. They read each graph back with `ORDER BY _id`, which is file order inside the graph.
  Our arrays keep file order: `test_first_rows_of_raw_file_match_graph_0` re-reads the first 5,000 lines of all.tsv and
  checks they encode to exactly what `graph_0.npz` stores, and t starts at 1.
- [x] **The t offset question is closed.** The reference uses `t = _id`, a global counter, not one that restarts per graph.
  Ours is the same: `test_t_is_global_line_number` checks t is 1..89,770,902 with no gaps, strictly +1 inside every graph,
  and each graph's first t is the previous graph's last t + 1. So t is identical to the authors' `_id` for every row they keep.
  The offset does not matter to the paper-faithful model anyway: only the order and the differences between t values are used.

## Difference found: the authors' loader drops the last 902 rows

`preprocess.py` only inserts when its buffer reaches 10,000 rows and never flushes the remainder after the loop.
89,770,902 = 8,977 x 10,000 + 902, so the authors' database is missing the **last 902 lines of all.tsv**, all from
**graph 599** (CNN, a benign test graph with 225,533 edges; they keep 224,631). Our streaming loader keeps them.
Effect on the Table 4 row: at most one benign test graph's score, very likely none. Recorded as deviation D-20;
the authors'-repo cross-check (M3-07) should confirm it by counting rows in their table.

## Consequences

- No database server to install: `make graphs` needs only Python, takes under 3 minutes and under 1 GB of RAM.
- t is the same as the authors' `_id` (D-04), so time order is not a source of difference between our run and theirs.
