# ADR-0005: Renumber node ids to 0..N-1

Status: proposed; evidence to be measured in story M2-09.

The authors' StreamSpot code allocates a node-memory table for 5,045,000 nodes (summary of the repo; check), and their README asks
for at least 64 GB. The paper's Table 2 counts 999,999 nodes for the whole dataset. A pipeline that only runs on one big machine
does not qualify for the clean-checkout criteria, and a 10-15 minute live run needs a small footprint.
Decision: IdCompactor renumbers node ids bijectively in first-seen order. With the cross-entropy decoder node ids are only
indices, so this is lossless. In the authors' variant, negative sampling draws over the id range, so compaction can change those
draws: run that ablation both ways on a subset and report the difference.
Evidence to collect: [ ] distinct node count from `make stats`; [ ] memcheck with and without compaction; [ ] identical scores on a subset.
