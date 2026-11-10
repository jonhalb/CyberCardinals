#!/usr/bin/env python
"""Environment stack check: can this machine train a KAIROS-style temporal graph network?

    conda activate kairos
    make graphs                       # needs data/processed/graph_100.npz
    python scripts/stack_check.py .

Trains a tiny TGN (GRU node memory + TransformerConv + MLP edge-type decoder, cross-entropy)
on ONE training graph (Gmail, id 100) for 2 epochs and prints the loss and speed. If the loss
prints and goes down, torch 1.13.1 + PyG 2.0.0 work here and the model can be built on this
machine. This is a smoke test, not the project's model (stories M3-01..M3-04 are): it skips
the per-batch memory bookkeeping, validation, scoring and every config choice.
Verified on 2026-11-09: loss 3.25 -> 3.07 over 2 epochs, about 50,000 edges/s on 2 CPU cores.
"""
import sys, time, numpy as np, torch
sys.path.insert(0, (sys.argv[1] if len(sys.argv) > 1 else ".") + "/src")
import torch_geometric
from torch_geometric.nn import TransformerConv
from torch_geometric.nn.models.tgn import TGNMemory, IdentityMessage, LastAggregator, LastNeighborLoader
from kairos_repro.data.graph_encoding import one_hot_msg
print("torch", torch.__version__, "pyg", torch_geometric.__version__)
torch.manual_seed(0)
root = sys.argv[1] if len(sys.argv) > 1 else "."
g = dict(np.load(root + "/data/processed/graph_100.npz"))  # a training graph (Gmail)
src = torch.from_numpy(g["src"].astype(np.int64)); dst = torch.from_numpy(g["dst"].astype(np.int64))
base = int(min(src.min(), dst.min())); src -= base; dst -= base
t = torch.from_numpy(g["t"]); msg = torch.from_numpy(one_hot_msg(g["src_type"], g["edge_type"], g["dst_type"]))
y = torch.from_numpy(g["edge_type"].astype(np.int64))
N = int(max(src.max(), dst.max())) + 1; MEM, TD, EMB, MSG = 100, 100, 200, msg.size(1)
memory = TGNMemory(N, MSG, MEM, TD, message_module=IdentityMessage(MSG, MEM, TD), aggregator_module=LastAggregator())
class Enc(torch.nn.Module):
    def __init__(s):
        super().__init__(); s.time_enc = memory.time_enc
        s.conv = TransformerConv(MEM, EMB // 2, heads=2, dropout=0.1, edge_dim=MSG + TD)
    def forward(s, x, last_update, edge_index, et, emsg):
        rel = s.time_enc((last_update[edge_index[0]] - et).float())
        return s.conv(x, edge_index, torch.cat([rel, emsg], -1))
enc = Enc(); dec = torch.nn.Sequential(torch.nn.Linear(2 * EMB, 100), torch.nn.ReLU(), torch.nn.Linear(100, 26))
loader = LastNeighborLoader(N, size=20); assoc = torch.empty(N, dtype=torch.long)
opt = torch.optim.Adam(set(memory.parameters()) | set(enc.parameters()) | set(dec.parameters()), lr=1e-4)
for epoch in range(2):
    memory.reset_state(); loader.reset_state(); tot = 0; t0 = time.time()
    for i in range(0, src.numel(), 1024):
        s_, d_, t_, m_, y_ = src[i:i+1024], dst[i:i+1024], t[i:i+1024], msg[i:i+1024], y[i:i+1024]
        opt.zero_grad()
        n_id = torch.cat([s_, d_]).unique(); n_id, ei, e_id = loader(n_id); assoc[n_id] = torch.arange(n_id.size(0))
        z, lu = memory(n_id); z = enc(z, lu, ei, t[e_id], msg[e_id])
        out = dec(torch.cat([z[assoc[s_]], z[assoc[d_]]], -1)); loss = torch.nn.functional.cross_entropy(out, y_)
        loss.backward(); opt.step(); memory.update_state(s_, d_, t_, m_); loader.insert(s_, d_); memory.detach()
        tot += loss.item() * s_.numel()
    print("epoch", epoch, "edges", src.numel(), "mean loss %.4f" % (tot / src.numel()), "time %.1fs" % (time.time() - t0))
