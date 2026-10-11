"""Aggregate recorded pilot results and make local plots/listening page."""
import json
from pathlib import Path
import numpy as np

def summarize(root):
    root=Path(root)
    training=json.loads((root/'training/training_report.json').read_text())
    generation=json.loads((root/'generation_benchmark.json').read_text())
    dataset=json.loads((root/'data/dataset_report.json').read_text())
    rows=[]
    for item in generation['results']:
        runs=[r for r in training['results'] if r['kind']==item['kind']]
        nll=[r['validation']['nll'] for r in runs]
        rows.append(dict(model=item['kind'],seeds=len(runs),validation_nll_mean=float(np.mean(nll)),
            validation_nll_sd=float(np.std(nll,ddof=1)) if len(runs)>1 else None,
            pitch_accuracy_mean=float(np.mean([r['validation']['pitch_accuracy'] for r in runs])),
            duration_accuracy_mean=float(np.mean([r['validation']['duration_accuracy'] for r in runs])),
            training_seconds_mean=float(np.mean([r['training_seconds'] for r in runs])),
            parameters_or_markov_stored_counts=runs[0]['parameters'],
            generation_seconds_mean=item['mean_inference_seconds'],
            rhythm_js_mean=item['mean_rhythm_js'],training_8gram_match_fraction=item['mean_training_8gram_match_fraction'],
            lag4_pitch_correlation_mean=item['mean_lag4_correlation']))
    summary=dict(dataset={k:v for k,v in dataset.items() if k not in ('rejected','transformations')},
        benchmark=rows,ablations=training['ablations'],equivalence=training['equivalence'],
        selected_checkpoint=training['selected_quantum_checkpoint'],
        selected_checkpoint_sha256=next(r['checkpoint_sha256'] for r in training['results'] if r.get('checkpoint')==training['selected_quantum_checkpoint']),
        training_seconds=training['total_seconds'],
        peak_rss_gib=max(r.get('peak_rss_bytes',0) for r in training['results'])/2**30,
        synthetic_initial_nll=training['synthetic']['initial_validation']['nll'],
        synthetic_final_nll=training['synthetic']['validation']['nll'],
        all_seed_results=[{k:v for k,v in r.items() if k!='history'} for r in training['results']],
        histories={r['kind']+'-'+str(r['seed']):r['history'] for r in training['results'] if 'history' in r},
        examples={name:json.loads((root/'examples'/name/'generation.json').read_text())['diagnostics'] for name in ('free','structured')},
        artifact_verification=json.loads((root/'artifact_verification.json').read_text()))
    (root/'pilot-summary.json').write_text(json.dumps(summary,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    labels=['QNN full','QNN short','Small classical','Large classical','Markov']
    bars=ax.bar(labels,[r['validation_nll_mean'] for r in rows],
        yerr=[r['validation_nll_sd'] or 0 for r in rows],capsize=4,
        color=['#7856a6','#a599bd','#2e8c94','#4d6879','#7b8e49'])
    for bar,row in zip(bars,rows):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.09,f"{row['validation_nll_mean']:.3f}",ha='center')
    ax.set(ylim=(0,4.8),ylabel='Validation NLL (nats / event; lower is better)',
           title='48-angle QNN pilot: classical baselines perform better\n6 validation pieces, 218 events; mean ± sample SD over 3 seeds (Markov deterministic)')
    ax.spines[['top','right']].set_visible(False);fig.savefig(root/'validation-comparison.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,5),layout='constrained',sharex=True,sharey=True)
    for ax,name in zip(axes,('free','structured')):
        trace=json.loads((root/'examples'/name/'generation.json').read_text())
        from .encoding import Event
        for row in trace['events']:
            e=Event(**row['event'])
            if e.pitch:ax.plot([e.onset/8,(e.onset+e.units)/8],[e.midi,e.midi],lw=4,
                color='#b46d33' if row['origin']=='classical_phrase_transform' else '#7856a6',solid_capstyle='butt')
        ax.set(title=name+' — purple: QNN sampled; orange: classical phrase transform',ylabel='MIDI pitch')
        ax.set_xticks(range(17));ax.grid(axis='x',alpha=.2)
    axes[-1].set_xlabel('Bars (16 × 4/4, 120 BPM = 32 seconds)')
    fig.savefig(root/'generated-melodies.png',dpi=160);plt.close(fig)
    blocks=[]
    for name in ('free','structured'):
        for mode in ('melody','arranged'):
            path=f'examples/{name}/{mode}'
            blocks.append(f'<section><h2>{name} / {mode}</h2><audio controls preload="metadata" src="{path}.wav"></audio> <a href="{path}.mid">MIDI</a> · <a href="examples/{name}/generation.json">Provenance</a></section>')
    html='<!doctype html><meta charset="utf-8"><title>OxfordQ long-form QNN pilot</title><style>body{max-width:900px;margin:40px auto;font:18px system-ui;padding:20px}audio{width:70%}section{padding:12px;border-bottom:1px solid #ddd}img{width:100%}</style><h1>Long-form QNN pilot — local listening examples</h1><p>Both examples are 16 bars / 32 seconds. Offline statevector generation. The pilot loses to classical baselines and has not established learned long-range structure.</p><p>Free melody: every pitch/rest/duration sampled by the QNN. Structured: A and B sampled; A′ and A″ are explicit classical phrase transformations. Arranged versions add deterministic classical accompaniment without changing melody events.</p>'+''.join(blocks)+'<img src="validation-comparison.png" alt="Validation NLL comparison"><img src="generated-melodies.png" alt="Generated melody piano rolls">'
    (root/'listen.html').write_text(html,encoding='utf-8')
    return summary

if __name__=='__main__':
    import sys
    result=summarize(sys.argv[1] if len(sys.argv)>1 else Path(__file__).parent/'artifacts')
    print(json.dumps(result['benchmark'],indent=2))
