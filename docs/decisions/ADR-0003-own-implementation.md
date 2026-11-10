# ADR-0003: We rebuild the pipeline; the paper-faithful model is the headline

Status: accepted.

Course text: "Rebuild its pipeline end to end, on your own machine." The reproduction rubric gives 30% to fidelity to the paper
(values the paper states are followed; deviations documented) and 35% to a pipeline that runs from a clean checkout.
Decision: the headline track follows the paper (configs/paper_faithful.json). The authors' StreamSpot-code settings run as an
ablation (configs/authors_variant.json). The authors' repo is run once as an external cross-check (results/authors_repo/) and
never copied into our source. Values we take from it are rows in docs/deviations.md.
