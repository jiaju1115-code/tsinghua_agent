"""Deterministic, epoch-aware family sampling for Pilot V0."""
import random
from collections import Counter
try:
    from torch.utils.data import Sampler
except ImportError:
    class Sampler: pass

class EpochAwareFamilySampler(Sampler):
    def __init__(self, task_families, seed=42, mathematical_reasoning_ratio=0.35, num_samples=None):
        self.task_families=list(task_families); self.seed=int(seed); self.target=float(mathematical_reasoning_ratio)
        self.num_samples=num_samples or len(self.task_families); self.epoch=0; self.history=[]
        self.math=[i for i,x in enumerate(self.task_families) if x=='MATHEMATICAL_REASONING']
        self.nonmath=[i for i,x in enumerate(self.task_families) if x!='MATHEMATICAL_REASONING']
        if not self.math or not self.nonmath: raise ValueError('FAMILY_SAMPLER_REQUIRES_MATH_AND_NONMATH')
    def set_epoch(self, epoch): self.epoch=int(epoch)
    def __len__(self): return self.num_samples
    def __iter__(self):
        rng=random.Random(self.seed+self.epoch)
        math_n=round(self.num_samples*self.target); nonmath_n=self.num_samples-math_n
        chosen=[rng.choice(self.math) for _ in range(math_n)]+[rng.choice(self.nonmath) for _ in range(nonmath_n)]
        rng.shuffle(chosen)
        families=Counter(self.task_families[i] for i in chosen)
        unique=len(set(chosen)); stat={'epoch':self.epoch,'sample_count':len(chosen),'families':{k:{'sampled_count':v,'sampled_ratio':round(v/len(chosen),6)} for k,v in sorted(families.items())},'unique_examples_seen':unique,'duplicate_exposure':len(chosen)-unique,'mathematical_reasoning_ratio':round(families['MATHEMATICAL_REASONING']/len(chosen),6),'target_ratio':self.target,'status':'PASS' if abs(families['MATHEMATICAL_REASONING']/len(chosen)-self.target)<=0.01 else 'WARN'}
        self.history.append(stat); self.epoch+=1
        return iter(chosen)
