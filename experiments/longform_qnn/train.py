"""Bounded deterministic CPU pilot; validation selection; no test-score access."""
import hashlib
import json
from pathlib import Path
import time
import platform
import numpy as np
import psutil
import torch
from .data import load_examples
from .encoding import Event, FEATURES, LONG, teacher_examples
from .models import ClassicalNet, Markov
from .quantum import QuantumModel, verify_equivalence

def make_model(kind,seed):
    if kind.startswith('qnn'):
        return QuantumModel(seed)
    return ClassicalNet(seed,large=kind=='classical_large')

def inputs(arrays, mode='full', permute_seed=None):
    x,y,r=arrays; x=x.copy()
    if mode=='short': x[:,LONG]=0
    if permute_seed is not None:
        # Matched bar position to avoid a mere phrase-clock distribution shift.
        rng=np.random.default_rng(permute_seed)
        for clock in np.unique(x[:,37]):
            idx=np.flatnonzero(x[:,37]==clock)
            x[idx,LONG]=x[rng.permutation(idx),LONG]
    return torch.tensor(x),torch.tensor(y,dtype=torch.long),torch.tensor(r,dtype=torch.long)

def evaluate(model, arrays, mode='full', permute_seed=None):
    x,y,r=inputs(arrays,mode,permute_seed); predictions=[]
    start=time.perf_counter()
    with torch.no_grad():
        for i in range(0,len(y),128): predictions.append(model(x[i:i+128],r[i:i+128]))
    p=torch.cat(predictions); target=p[torch.arange(len(y)),y]
    losses=-torch.log(target)
    pitch=p.reshape(-1,15,8).sum(dim=2).argmax(dim=1)
    duration=p.reshape(-1,15,8).sum(dim=1).argmax(dim=1)
    return dict(nll=float(losses.mean()),pitch_accuracy=float((pitch==y//8).double().mean()),
        duration_accuracy=float((duration==y%8).double().mean()),events=len(y),
        inference_seconds=time.perf_counter()-start), losses.numpy()

def save_checkpoint(model,path,metadata):
    payload=dict(metadata,weights={k:v.detach().cpu().tolist() for k,v in model.state_dict().items()})
    data=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    Path(path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()

def load_checkpoint(path):
    payload=json.loads(Path(path).read_text()); model=make_model(payload['kind'],payload['seed'])
    original=model.state_dict()
    model.load_state_dict({k:torch.tensor(v,dtype=original[k].dtype) for k,v in payload['weights'].items()})
    model.eval(); return model,payload

def train_one(kind,seed,train,val,out,steps,batch,deadline,memory_gib=4):
    mode='short' if kind=='qnn_short' else 'full'
    model=make_model(kind,seed); x,y,r=inputs(train,mode)
    optimizer=torch.optim.Adam(model.parameters(),lr=.025 if kind.startswith('qnn') else .003)
    rng=np.random.default_rng(seed); history=[]; start=time.perf_counter(); peak=0
    best=float('inf'); selected=0; checkpoint=Path(out)/f'{kind}-{seed}.json'
    initial,_=evaluate(model,val,mode)
    best=initial['nll']
    save_checkpoint(model,checkpoint,dict(kind=kind,seed=seed,step=0,mode=mode))
    completed=0
    for step in range(1,steps+1):
        rss=psutil.Process().memory_info().rss; peak=max(peak,rss)
        if rss > memory_gib*1024**3:
            raise MemoryError('Declared resident-memory budget exceeded; training stopped')
        if time.perf_counter() > deadline:
            break
        idx=rng.integers(0,len(y),size=batch)
        optimizer.zero_grad(set_to_none=True)
        p=model(x[idx],r[idx]); loss=-torch.log(p[torch.arange(batch),y[idx]]).mean()
        if not torch.isfinite(loss): raise FloatingPointError('Nonfinite NLL')
        loss.backward()
        norm=float(torch.nn.utils.clip_grad_norm_(model.parameters(),5))
        if not np.isfinite(norm): raise FloatingPointError('Nonfinite gradient')
        optimizer.step(); completed=step
        if step==1 or step%40==0 or step==steps:
            stats,_=evaluate(model,val,mode)
            history.append(dict(iteration=step,training_batch_nll=float(loss.detach()),
                validation_nll=stats['nll'],gradient_norm=norm,elapsed_seconds=time.perf_counter()-start))
            if stats['nll'] < best:
                best=stats['nll']; selected=step
                save_checkpoint(model,checkpoint,dict(kind=kind,seed=seed,step=step,mode=mode))
            print(json.dumps(dict(model=kind,seed=seed,**history[-1])),flush=True)
    model,_=load_checkpoint(checkpoint)
    validation,losses=evaluate(model,val,mode)
    training,_=evaluate(model,train,mode)
    report=dict(kind=kind,seed=seed,parameters=model.parameter_count(),requested_steps=steps,
        completed_steps=completed,selected_step=selected,initial_validation=initial,
        validation=validation,training=training,training_seconds=time.perf_counter()-start,
        peak_rss_bytes=peak,checkpoint=checkpoint.name,
        checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),history=history,
        runtime_budget_hit=completed<steps)
    return model,report,losses

def synthetic_check(out,deadline):
    # Two bar-alternating patterns; real causal prefixes, deterministic teacher forcing.
    examples=[]
    for offset in range(4):
        events=[]
        for t in range(0,128,2): events.append(Event(1 if (t//8+offset)%2==0 else 5,2,t))
        examples.append(teacher_examples(events))
    arrays=tuple(np.concatenate([a[i] for a in examples]) for i in range(3))
    model,report,_=train_one('qnn_synthetic',13,arrays,arrays,out,80,64,deadline)
    # This is a numerical overfit check, explicitly not held-out performance.
    if not report['validation']['nll'] < report['initial_validation']['nll']-.15:
        raise AssertionError('Synthetic teacher-forcing learning check failed')
    return report

def bootstrap_piece_delta(full,other,pieces,seed=921):
    ends=np.cumsum([len(p['events']) for p in pieces]); starts=np.r_[0,ends[:-1]]
    deltas=np.array([(other[a:b]-full[a:b]).mean() for a,b in zip(starts,ends)])
    rng=np.random.default_rng(seed)
    means=np.mean(rng.choice(deltas,(2000,len(deltas)),replace=True),axis=1)
    return dict(mean_piece_nll_delta=float(deltas.mean()),ci95=np.quantile(means,[.025,.975]).tolist(),
                interpretation='positive means full context lower NLL; exploratory piece bootstrap, correlated training seeds, validation only')

def run(data_dir,out,steps=320,seeds=(11,22,33),budget_seconds=1800,memory_gib=4):
    if budget_seconds > 3*3600 or budget_seconds <= 0:
        raise ValueError('First-pass total training budget must be 0..10800 seconds')
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    equivalence=verify_equivalence()  # compulsory gate before ANY training
    start=time.perf_counter(); deadline=start+budget_seconds
    budget=dict(total_seconds=budget_seconds,memory_gib=memory_gib,threads=1,seeds=list(seeds),
        steps_per_model=steps,batch_size=64,parameter_count_qnn=48,python=platform.python_version(),
        torch=torch.__version__,device='CPU exact statevector',epsilon=1e-9)
    (out/'budget.json').write_text(json.dumps(budget,indent=2))
    synthetic=synthetic_check(out,deadline)
    train,training_pieces=load_examples(data_dir,'train'); val,validation_pieces=load_examples(data_dir,'validation')
    results=[]; ablations=[]
    for seed in seeds:
        full_losses=None
        for kind in ('qnn_full','qnn_short','classical_small','classical_large'):
            if time.perf_counter() >= deadline:
                break
            model,report,losses=train_one(kind,seed,train,val,out,steps,64,deadline,memory_gib)
            results.append(report)
            if kind=='qnn_full':
                full_losses=losses
                removed,rl=evaluate(model,val,'short')
                permuted,pl=evaluate(model,val,permute_seed=777)
                ablations.append(dict(seed=seed,full=report['validation'],removed=removed,permuted=permuted,
                    removed_delta=bootstrap_piece_delta(losses,rl,validation_pieces),
                    permuted_delta=bootstrap_piece_delta(losses,pl,validation_pieces)))
            elif kind=='qnn_short' and full_losses is not None:
                ablations[-1]['short_retrained']=report['validation']
                ablations[-1]['short_delta']=bootstrap_piece_delta(full_losses,losses,validation_pieces)
            (out/'progress.json').write_text(json.dumps(dict(results=results,ablations=ablations),indent=2))
        if time.perf_counter() >= deadline: break
    t=time.perf_counter(); markov=Markov().fit(train[0],train[1]); fit=time.perf_counter()-t
    markov_eval,_=evaluate(markov,val)
    results.append(dict(kind='markov',seed=None,parameters=markov.parameter_count(),validation=markov_eval,training_seconds=fit))
    best=min((r for r in results if r['kind']=='qnn_full'),key=lambda r:r['validation']['nll'])
    report=dict(budget=budget,equivalence=equivalence,synthetic=synthetic,results=results,
        ablations=ablations,selected_quantum_checkpoint=best['checkpoint'],
        selection='lowest validation NLL over full-context QNN seeds/iterations; test unused',
        total_seconds=time.perf_counter()-start,test_evaluations=0,
        training_events=len(train[1]),validation_events=len(val[1]),
        limitations=['Small fixed encoder and 48 circuit angles; no architecture search',
                    'Baselines share features/examples/batch schedule; capacities and optimizer rates differ',
                    'Validation reused for checkpoint/seed selection; bootstrap is exploratory, not test inference',
                    'Exact statevector probabilities, no finite-shot or hardware claim'])
    (out/'training_report.json').write_text(json.dumps(report,indent=2))
    return report
