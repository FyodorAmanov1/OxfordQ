"""Matched-seed generation diagnostics; model selection uses validation NLL only."""
import json
from pathlib import Path
import numpy as np
import torch
from .data import load_examples
from .train import load_checkpoint
from .models import Markov
from .generate import sample,diagnostics

def run(artifacts):
    root=Path(artifacts);report=json.loads((root/'training/training_report.json').read_text())
    train,pieces=load_examples(root/'data','train');torch.set_num_threads(1)
    results=[]
    for kind in ('qnn_full','qnn_short','classical_small','classical_large','markov'):
        candidates=[r for r in report['results'] if r['kind']==kind]
        if not candidates:continue
        selected=min(candidates,key=lambda r:r['validation']['nll'])
        model=Markov().fit(train[0],train[1]) if kind=='markov' else load_checkpoint(root/'training'/selected['checkpoint'])[0]
        examples=[]
        for seed in (101,102,103):
            events,trace=sample(model,seed,mode='short' if kind=='qnn_short' else 'full')
            examples.append(dict(seed=seed,**diagnostics(events,pieces),inference_seconds=trace['inference_seconds']))
        results.append(dict(kind=kind,selection_seed=selected['seed'],examples=examples,
            mean_inference_seconds=float(np.mean([e['inference_seconds'] for e in examples])),
            mean_event_count=float(np.mean([e['events'] for e in examples])),
            mean_rhythm_js=float(np.mean([e['rhythm_js_divergence'] for e in examples])),
            mean_training_8gram_match_fraction=float(np.mean([e['training_8gram_match_fraction'] for e in examples])),
            mean_lag4_correlation=float(np.mean([e['previous_four_bar_mean_pitch_correlation'] for e in examples if e['previous_four_bar_mean_pitch_correlation'] is not None]))))
    result=dict(results=results,notes=['Three matched sampling seeds; selected model checkpoint per family using validation NLL',
        'CPU single-event exact differentiable simulator timings; no finite-shot executions',
        'Lag-4 summary correlation and n-grams are exploratory diagnostics, not evidence of learned form',
        'No human listening panel or perceptual quality score'])
    (root/'generation_benchmark.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    import sys
    run(sys.argv[1] if len(sys.argv)>1 else Path(__file__).parent/'artifacts')
