# Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Pipeline only runs on one member's machine (the rubric says that does not qualify) | Medium | High | Node-id compaction (ADR-0005); memcheck on all three machines; outsider clean-checkout test |
| R2 | Memory needs exceed laptops (authors' README says at least 64 GB for their fixed table) | Medium | High | Compaction to the real node count; measure in M2-09 before building the model |
| R3 | Live run too slow for a 10-15 minute talk | Medium | High | Time the full run early; define `QUICK=1`; recorded fallback in docs/demo/ |
| R4 | Board filled in near the deadline (scores Missing) | Medium | High | Size stories now; move cards weekly; milestones and iterations set from day one |
| R5 | Uneven story points, so unfair individual grades | Medium | Medium | Points planned per member in docs/backlog.csv are balanced; re-balance at each iteration review |
| R6 | Result depends on the seed or on test-time randomness | Medium | Medium | Seeds 0-4 and 12345; deterministic test pass for the cross-entropy decoder; margin analysis |
| R7 | The plan's facts about the authors' code are wrong (they are from summaries) | Medium | Medium | Confirm each `check` row in docs/deviations.md against the source file before relying on it |
| R8 | PyG 2.0.0 will not install on someone's OS | Medium | Medium | WSL2 Ubuntu 22.04; one working Linux machine is enough for official runs |
| R9 | Dataset host changes or disappears | Low | High | Keep a verified copy of all.tar.gz on the team Drive; SHA-256 check in `make data` |
| R10 | Missed presentation slot (15% off the capstone) or late deliverable (zero) | Low | Very high | Put every date in docs/schedule.md; dry run a week early |
| R11 | Another team claims KAIROS | Low | High | Confirm approval of our paper with Dr. Parra now |
