"""Reproduce original + one refined composition from saved samples; never resample."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import wave
import numpy as np

from experiments.qcbm_composition.composition import compose, harmonize, canonical
from experiments.qcbm_composition.render import export
from .refine import refine
from .analysis import compare
from .page import write_page

HERE = Path(__file__).resolve().parent

def digest(data):
    return hashlib.sha256(data).hexdigest()

def load_samples():
    contents = (HERE/'data/raw-samples.json').read_bytes()
    manifest = json.loads((HERE/'data/reference-manifest.json').read_bytes())
    if digest(contents) != manifest['raw_sha256']:
        raise ValueError('Preserved quantum sample bytes changed')
    raw = json.loads(contents)
    if raw['seed'] != 20261011 or len(raw['motifs']) != 16 or raw['backend_jobs'] != 0:
        raise ValueError('Unexpected preserved sample')
    for index,m in enumerate(raw['motifs']):
        if m['motif_id'] != f'm{index:02}' or int(m['bitstring'],2) != m['basis_index'] or m['tokens'] != [(m['basis_index']>>(3*j))&7 for j in range(4)]:
            raise ValueError('Invalid preserved motif identity/bit ordering')
    return raw,contents,manifest

def match_loudness(path, reference):
    def read(p):
        with wave.open(str(p)) as w:
            return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
    audio, target = read(path),read(reference)
    rms = float(np.sqrt(np.mean(audio**2)))
    target_rms = float(np.sqrt(np.mean(target**2)))
    gain = min(target_rms/rms,.95/float(np.max(np.abs(audio))))
    mastered = (audio*gain*32768).astype('<i2')
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(22050)
        stream.writeframes(mastered.tobytes())
    final = mastered.astype(float)/32768
    return dict(origin='classical_comparison_loudness_match',gain=gain,gain_db=float(20*np.log10(gain)),
        input_rms=rms,reference_rms=target_rms,final_rms=float(np.sqrt(np.mean(final**2))),
        final_peak=float(np.abs(final).max()),note='One scalar gain; no compression or change to MIDI velocities')

def run(out):
    out=Path(out)
    if out.exists():
        raise ValueError('Output already exists; choose a fresh --out to preserve artifacts')
    raw,raw_bytes,manifest = load_samples()
    snapshot = canonical(raw)
    original = compose(raw)
    h,b,c = harmonize(original['events'])
    for e in b+c:
        e['bar']=int(e['onset']//4)
    original_data=dict(events=original['events'],bass=b,chords=c,harmony=h)
    improved = refine(raw)
    out.mkdir(parents=True)
    (out/'raw-samples.json').write_bytes(raw_bytes)
    original_tracks=[('Classically developed QCBM melody',original['events'])]
    export(out,'original-melody',original_tracks)
    export(out,'original-arranged',original_tracks+[('Classical bass',b),('Classical chords',c)])
    for name,expected in manifest['reference_files'].items():
        if digest((out/f'original-{name}').read_bytes()) != expected:
            raise AssertionError(f'Original PR #8 output changed: {name}')
    improved_tracks=[('Classically developed QCBM melody',improved['events'])]
    audio=dict(melody=export(out,'improved-melody',improved_tracks),
               arranged=export(out,'improved-arranged',improved_tracks+[('Classical bass',improved['bass']),('Classical chords',improved['chords'])]))
    matching={texture:match_loudness(out/f'improved-{texture}.wav',out/f'original-{texture}.wav') for texture in ('melody','arranged')}
    for match in matching.values():
        match['source_event_ids']=sorted({e['source_event_id'] for e in improved['events']})
        match['raw_samples_sha256']=digest(raw_bytes)
    if canonical(raw) != snapshot or raw_bytes != (HERE/'data/raw-samples.json').read_bytes():
        raise AssertionError('Source mutated during refinement')
    analysis = compare(original_data,{k:improved[k] for k in ('events','bass','chords','harmony')})
    trace=dict(schema='oxfordq.qcbm-refinement.v1',created_utc=datetime.now(timezone.utc).isoformat(),
        data_status='PRE-GENERATED',execution='OFFLINE classical refinement of existing saved samples',
        backend_jobs=0,statevector_evaluations=0,sampling_calls=0,training_steps=0,
        bars=16,beats=64,tempo_bpm=120,seconds=32,structure=['A',"A'",'B',"A''"],
        source=dict(reference_commit=manifest['reference_commit'],raw_samples_file='raw-samples.json',
            raw_samples_sha256=digest(raw_bytes),original_checkpoint_sha256=raw['original_checkpoint_sha256'],
            checkpoint_file_sha256=raw['checkpoint_file_sha256'],distribution_sha256=raw['distribution_sha256'],seed=raw['seed'],
            preserved_tokens=64,preserved_motifs=16),
        original=dict(**original,reference_files=manifest['reference_files']),
        improved=improved,audio=audio,loudness_matching=matching,
        interpretation='All refinements are classical; no CHSH evidence or new quantum execution; subjective quality pending')
    for name,value in [('trace',trace),('harmonic-analysis',improved['harmony']),('analysis',analysis)]:
        (out/f'{name}.json').write_bytes(canonical(value))
    write_page(out,trace,analysis)
    outputs={p.name:dict(sha256=digest(p.read_bytes()),bytes=p.stat().st_size) for p in sorted(out.iterdir()) if p.is_file()}
    (out/'manifest.json').write_bytes(canonical(dict(schema='oxfordq.qcbm-refinement-artifacts.v1',files=outputs)))
    print(json.dumps(dict(output=str(out.resolve()),raw_sha256=digest(raw_bytes),
        progression=[h['chord'] for h in improved['harmony']],analysis=analysis,loudness_matching=matching),indent=2))
    return trace

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=HERE/'artifacts/listening')
    run(parser.parse_args().out)
