"""Classical benchmarks with exactly the QNN's available causal features."""
from collections import defaultdict
import numpy as np
import torch
from torch import nn
from .encoding import FEATURES
from .quantum import normalize_legal

class ClassicalNet(nn.Module):
    def __init__(self, seed, large=False):
        super().__init__(); torch.manual_seed(seed)
        widths = [FEATURES, 128, 128, 120] if large else [FEATURES, 32, 120]
        layers = []
        for a,b in zip(widths[:-1],widths[1:]):
            layers.extend([nn.Linear(a,b), nn.Tanh()])
        self.net = nn.Sequential(*layers[:-1]).double()
    def forward(self,x,remaining):
        return normalize_legal(torch.softmax(self.net(x),dim=-1),remaining)
    def parameter_count(self):
        return sum(p.numel() for p in self.parameters())

class Markov:
    """Dirichlet-smoothed backoff over full context, last 2 events, last event.

    Full features (including four-bar summaries) are exposed via quantized keys.
    Sparse full-context counts back off continuously; no validation fitting.
    """
    def __init__(self, alpha=8.):
        self.alpha=alpha; self.tables=[defaultdict(lambda:np.zeros(120)) for _ in range(3)]
        self.unigram=np.ones(120)*.1
    def keys(self,x):
        return [tuple(np.round(x[:4]*16).astype(int)),
                tuple(np.round(x[:8]*16).astype(int)),
                tuple(np.round(x*8).astype(int))]
    def fit(self,x,y):
        for row,target in zip(x,y):
            self.unigram[target]+=1
            for table,key in zip(self.tables,self.keys(row)):
                table[key][target]+=1
        return self
    def __call__(self,x,remaining):
        rows=[]
        for row in x.detach().numpy():
            p=self.unigram/self.unigram.sum()
            for table,key in zip(self.tables,self.keys(row)):
                counts=table.get(key)
                if counts is not None:
                    p=(counts+self.alpha*p)/(counts.sum()+self.alpha)
            rows.append(p)
        return normalize_legal(torch.tensor(np.array(rows)),remaining)
    def parameter_count(self):
        return int(sum(np.count_nonzero(v) for t in self.tables for v in t.values())+120)
