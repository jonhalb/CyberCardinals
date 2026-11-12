# Choices the paper left open, and deviations from the paper and the authors' code

The paper does not state these; each row is a decision we made and why. "Source" says where the value came from.
`check` means it comes from a summary of the authors' repo and must be confirmed against the source file.
Add a row BEFORE using any new choice. Fidelity to the paper is 30% of the reproduction grade, and this file is how we show it.

| ID | Gap or deviation | Paper says | Our decision | Source | Could it move the number? | Status |
|---|---|---|---|---|---|---|
| D-01 | Learning rate, optimizer, epochs, batch size | not stated | Adam, 1e-4, 10 epochs, 1024 edges | authors' StreamSpot code | Yes | check |
| D-02 | Random seed | not stated (one run?) | seeds 0-4 plus the authors' 12345; PYTHONHASHSEED=0 | authors' code seeds torch with 12345 | Yes: the seed table measures it | check |
| D-03 | Node features on StreamSpot | 16-dim hierarchical hashing of paths/IPs | one-hot node type (8 dims): StreamSpot has no paths or IPs | authors' code | Yes | check |
| D-04 | Time | wall-clock timestamps | 1-based line number in all.tsv: the dataset README says preprocessing removed timestamps, so file order is the only time signal | dataset README | Low | decided (offset vs the authors' `_id`: check) |
| D-05 | Threshold rule | set from benign validation data (Sec. 4.3.3) | maximum validation graph score | authors' code | Yes | check |
| D-06 | SD in "mean + 1.5 SD" and empty-case rule | mean + 1.5 SD | population SD (ddof=0); if no edge exceeds the cut, score = mean error | our choice | Low | decided |
| D-07 | Number of edge types | nine (paper's setup) | 26, StreamSpot's own types | dataset | Structural | decided |
| D-08 | Attention heads, dropout, time encoder | not stated | 2 heads, dropout 0.1, PyG default time encoder | authors' code | Possible | check |
| D-09 | Rareness (IDF) | used to pick suspicious nodes | not used: with one window per graph the score formula never uses rareness | paper Sec. 4.3 | No | decided |
| D-10 | Queues and Louvain investigation | used | not run: not needed for the Table 4 row | paper Sec. 5.1.1 | No | decided |
| D-11 | Which graph trains each scenario | "one graph" | graphs 0, 100, 200, 400, 500 | authors' code | Yes | check |
| D-12 | Which graphs validate | "24 graphs" | x01 to x24 per benign scenario | authors' code | Yes | check |
| D-13 | Node ids | n/a | renumbered to 0..n-1 inside each graph (`localize`); lossless for the cross-entropy decoder (ADR-0005) | ours | None for P; may shift V's negative sampling | decided |
| D-14 | One-hot index order | n/a | fixed sorted alphabets (the reference builds maps by iterating Python sets, whose order varies between runs) | ours | No for our runs; breaks the authors' pre-trained model on our data | check |
| D-15 | Storage format | n/a | npz of type indices, message rebuilt per batch | ours | No | decided |
| D-16 | Library versions | PyG, scikit-learn, networkx named, no versions | torch 1.13.1, PyG 2.0.0, scikit-learn 1.2.0, networkx 2.8.7 | authors' requirements | No if matched | decided |
| D-17 | Node memory across graphs | one streaming graph per dataset | memory and neighbour state reset between graphs; the authors' code keeps one 5,045,000-row table | ours (ADR-0005) | Low: about 2,400 of 5.04M ids appear in more than one graph | decided |
| D-18 | Meaning of the edge embedding size | \|z\| = 200 (Sec. 5) | z = [source node embedding (100) ; destination node embedding (100)], so the encoder outputs 100 per node and the decoder reads 200 | our reading; the paper does not say how z is formed from the two endpoints | Possible | decided (check the authors' code) |
| D-19 | Batching | one edge at a time (Sec. 4.2) | 1,024 edges per step; edges in the same batch do not update each other's node state before being predicted | PyG TGN practice; authors' code (check) | Possible | decided |
