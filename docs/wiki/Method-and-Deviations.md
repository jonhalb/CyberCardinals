# Method and deviations

Story M4-02. Owner: Jonas Halbrook. This page says how our pipeline works, in the order it runs, and lists every
place where the paper leaves a choice open or where we do something different. The full table with sources and
dates is [`docs/deviations.md`](https://github.com/jonhalb/CyberCardinals/blob/main/docs/deviations.md); every row of it (D-01 to D-25) appears below.

We rebuilt the pipeline ourselves. The authors' repository (github.com/ubc-provenance/kairos, commit 0e0b633) was
read for values the paper does not state and is used as an outside cross-check. None of its files are copied.

## The pipeline, in the order it runs

| Step | What happens | Script | Command |
|---|---|---|---|
| 1. Download | Fetch `all.tar.gz` from the StreamSpot repository and check its SHA-256 | [`data/download.py`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/data/download.py) | `make data` |
| 2. Build graphs | Split all 89,770,902 rows (D-25) into 600 graphs; store each as small arrays of node ids, type codes and time (D-15) | [`data/build_graphs.py`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/data/build_graphs.py) | `make graphs` |
| 3. Describe the data | Count nodes, edges and types per graph; write the data report | [`data/stats.py`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/data/stats.py) | `make stats` |
| 4. Baselines | Score do-nothing (B0) and histogram distance (B1) on the same split, before the model | [`baselines/`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/baselines/histogram_distance.py) | `make baselines` |
| 5. Train | Train the model on five benign graphs, 10 epochs | [`model/train.py`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/model/train.py) | `make train` |
| 6. Score | Score the 120 validation and 475 test graphs; set the threshold; predict | [`model/evaluate.py`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/model/evaluate.py) | `make evaluate` |
| 7. Compare | Paper / ours / difference table | [`eval/compare.py`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/eval/compare.py) | `make compare` |

`make reproduce` runs steps 1 to 7 from an empty checkout. The split (which graphs train, validate and test) is
defined once in [`common.py`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/common.py) and imported everywhere.

## The data, as the model sees it
- 600 graphs, 100 per scenario. Graphs 300 to 399 are the drive-by-download attack; the rest are benign.
- Each row of the file is one edge: source node, destination node, and an edge type. There are 8 node types and
  26 edge types (D-07). The file has no timestamps, so an edge's time is its line number (D-04).
- Each edge carries a 42-number message: one-hot source type (8), one-hot edge type (26), one-hot destination
  type (8). The type order is fixed and sorted, so it is the same on every machine (D-14). There is no other node
  feature (D-03).
- The model handles one graph at a time. Inside a graph, node ids are renumbered to 0..n-1 (D-13), and the node
  memory is wiped before the next graph (D-17). We measured that this renumbering changes no score
  ([`results/id_check.md`](https://github.com/jonhalb/CyberCardinals/blob/main/results/id_check.md)) and keeps training under 0.5 GB of RAM.

## The model (track P, paper-faithful), in plain words
Code: [`model/paper_faithful.py`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/model/paper_faithful.py). Settings: [`configs/paper_faithful.json`](https://github.com/jonhalb/CyberCardinals/blob/main/configs/paper_faithful.json).

1. **Node memory.** Every node has a state of 100 numbers, all zero at the start of a graph. Each time a node
   takes part in an edge, a GRU updates its state from that edge's message and time (paper Sec. 4.2).
2. **Encoder.** To describe a node now, an attention layer (TransformerConv, 2 heads, dropout 0.1: D-08) mixes
   its state with those of its 20 most recent neighbours, using each past edge's message and how long ago it
   happened. This gives 100 numbers per node. An edge is described by its two endpoints together: 200 numbers
   (D-18).
3. **Decoder.** A small MLP, Linear(200,100), tanh, Linear(100,26), reads those 200 numbers and guesses the
   edge's type (D-20).
4. **Error.** The per-edge error is the cross-entropy of that guess against the true type. An edge the model
   did not expect has a large error.
5. **No peeking.** An edge is predicted only from edges before it. Edges are processed 1,024 at a time in file
   order (D-19); within a step the model predicts first, then learns, then adds the batch to the memory (D-21).
   A unit test changes a batch's edge types and checks its own embeddings do not move.
6. **Training.** Graphs 0, 100, 200, 400 and 500, one per benign scenario (D-11), in that order, never shuffled.
   Adam, learning rate 0.0001, 10 epochs (D-01). Seeds 0 to 4 and 12345 (D-02).
7. **Graph score.** Take the errors of all edges in a graph. Keep those above mean + 1.5 standard deviations
   and average them (paper Sec. 4.3; D-06). The paper's rareness weighting and queue-based investigation are
   not needed for this table row and are not run (D-09, D-10).
8. **Threshold and prediction.** The threshold is the largest score among the 120 validation graphs (x01 to x24
   of each benign scenario: D-12, D-05). A test graph is called an attack when its score is strictly greater.
   Details and the metric definitions, including the two kinds of AUC (D-24), are on the
   [Evaluation Protocol](Evaluation-Protocol) page.

Track V, the authors' variant ([`model/authors_variant.py`](https://github.com/jonhalb/CyberCardinals/blob/main/src/kairos_repro/model/authors_variant.py)), is an ablation: it replaces step 3 with the link-prediction decoder found
in the authors' StreamSpot code (D-22, D-23). It is never the headline.

Environment: Python 3.9, torch 1.13.1 (CPU), torch-geometric 2.0.0, scikit-learn 1.2.0, networkx 2.8.7 (D-16).

## Every deviation and open choice

"Could it move the number?" is our judgement of whether the choice can change the Table 4 result.

### A. Values the paper does not state, taken from the authors' code and confirmed against its source
| ID | Choice | Paper says | We use | Could it move the number? |
|---|---|---|---|---|
| D-01 | Optimizer, learning rate, epochs, batch size | not stated | Adam, 0.0001, 10 epochs, 1,024 edges | Yes |
| D-03 | Node features on StreamSpot | 16-number hashing of paths and IPs | one-hot node type inside the edge message; StreamSpot has no paths or IPs | Yes |
| D-04 | Time | wall-clock timestamps | line number in the file; the dataset has no timestamps | Low |
| D-05 | Threshold rule | "from benign validation data" | largest validation graph score; attack if strictly greater | Yes |
| D-08 | Attention heads, dropout, time encoder | not stated | 2 heads, dropout 0.1, PyG's time encoder | Possible |
| D-11 | Training graphs | "one graph" per scenario | 0, 100, 200, 400, 500 | Yes |
| D-12 | Validation graphs | "24 graphs" per scenario | x01 to x24 of each benign scenario | Yes |
| D-19 | Batching | one edge at a time | 1,024 edges per step; edges in a batch do not update each other's state before being predicted | Possible |

### B. Choices that are ours
| ID | Choice | Paper says | We use | Could it move the number? |
|---|---|---|---|---|
| D-02 | Random seeds | not stated | 0 to 4 and 12345. The authors do not seed training; their 12345 only fixes random draws while scoring, so 12345 as a training seed is our construct | Yes: the seed table measures it |
| D-06 | Standard deviation in "mean + 1.5 SD" | not stated which | population SD; if no edge is above the cut, the score is the mean error | Low |
| D-07 | Number of edge types | nine (the paper's general setup) | 26, StreamSpot's own types | Structural |
| D-13 | Node ids | not applicable | renumbered to 0..n-1 inside each graph; measured to change no score | None for track P |
| D-14 | One-hot order | not applicable | fixed sorted alphabets; the authors' code iterates Python sets, whose order can differ between runs | No for our runs |
| D-15 | Storage | not applicable | arrays of type codes per graph; the 42-number message is rebuilt per batch | No |
| D-16 | Library versions | libraries named, no versions | versions from the authors' requirements (listed above) | No if matched |
| D-17 | Node memory across graphs | one streaming graph per dataset | memory wiped between graphs; the authors keep one 5,045,000-row table | Low: about 2,400 of 5.04 million ids appear in more than one graph |
| D-18 | How the 200-number edge embedding is formed | size 200, construction not stated | source node (100) joined with destination node (100) | Possible |
| D-20 | Decoder size | "an MLP", no sizes | Linear(200,100), tanh, Linear(100,26). The authors' StreamSpot code has no edge-type decoder; their DARPA code uses a deeper MLP with dropout 0.5 | Possible |
| D-21 | Order inside a training step | not stated | predict from the past, update the weights, then add the batch to the memory | Low |
| D-25 | Rows loaded | all 89.8 million edges | all 89,770,902 lines. The authors' loader drops the last 902 lines (all in graph 599, a benign test graph) because its final partial batch is never written | Very low: one benign test graph loses 0.4% of its edges in their run |
| D-24 | AUC | reported, method not stated | AUC from the continuous scores, with the 0/1 version (the authors' method) next to it | Yes: they differ whenever a graph is misclassified |

### C. Parts of the paper we do not run
| ID | Part | Paper says | We do | Could it move the number? |
|---|---|---|---|---|
| D-09 | Rareness (IDF) weighting | used to pick suspicious nodes | not used: with one time window per graph the score never uses it | No |
| D-10 | Queues and community-based investigation | used for attack reconstruction | not run: not needed for the Table 4 row | No |

### D. Track V only (the authors' variant)
| ID | Choice | Authors' code | We use | Could it move the number? |
|---|---|---|---|---|
| D-22 | The random fake destination | drawn from their 5,045,000-row table, so almost always a never-seen node | same range; a draw that is not a node of the current graph goes to one reserved empty row | Low |
| D-23 | Memory during training | five training graphs joined into one stream, reset once per epoch | reset between the five graphs, as in D-17 | Low |

## What to remember when reading our result
The choices most able to move the number are the ones marked Yes or Possible: the training settings (D-01), the
seed (D-02), the threshold rule (D-05), the batch size (D-19), how the edge embedding is formed (D-18) and the
decoder size (D-20). The [Gap Explanation](Gap-Explanation) page ranks them against whatever difference we find.
