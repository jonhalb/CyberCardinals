# ADR-0002: Stream all.tsv instead of loading PostgreSQL

Status: draft; Emiliano completes the evidence in story M2-03.

The authors load the file into PostgreSQL and read each graph back ordered by a serial `_id`, which they use as time.
all.tsv is already sorted into 600 contiguous graph blocks, so we stream it and use the 1-based line number as t.
Evidence to collect: [ ] per-graph edge counts match the totals; [ ] ordering of first and last rows matches the `_id` order;
[ ] the t offset question is closed (the reference stores global ids, not per-graph restarts).
