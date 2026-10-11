"""Frozen showcase loader: literal Qollab paths, standard library, no execution."""
import base64
import json
from hashlib import sha256


def load_showcase():
    # Literal strings are required by Qollab's data-file discovery.
    paths = {
        'improved-melody.wav': 'data/composition/improved-melody.wav',
        'improved-arranged.wav': 'data/composition/improved-arranged.wav',
        'improved-melody.mid': 'data/composition/improved-melody.mid',
        'improved-arranged.mid': 'data/composition/improved-arranged.mid',
        'raw-samples.json': 'data/composition/raw-samples.json',
        'trace.json': 'data/composition/trace.json',
    }
    with open('data/composition/freeze.json', encoding='utf-8') as stream:
        freeze = json.load(stream)
    if (freeze['schema'] != 'oxfordq.composition-freeze.v1'
            or freeze['accepted_commit'] != '2801ba46ed5acdc7fbf0d3cca635f50aa8a2b88c'
            or freeze['data_status'] != 'PRE-GENERATED'
            or set(freeze['files']) != set(paths)):
        raise ValueError('Composition freeze identity mismatch')
    data = {}
    for name, path in paths.items():
        with open(path, 'rb') as stream:
            contents = stream.read()
        if sha256(contents).hexdigest() != freeze['files'][name]['sha256']:
            raise ValueError('Frozen composition asset changed: ' + name)
        data[name] = contents
    trace, raw = (json.loads(data[name]) for name in ('trace.json', 'raw-samples.json'))
    if (trace['schema'] != 'oxfordq.qcbm-refinement.v1'
            or trace['data_status'] != 'PRE-GENERATED'
            or (trace['bars'], trace['beats'], trace['tempo_bpm'], trace['seconds']) != (16, 64, 120, 32)
            or any(trace[k] != 0 for k in ('backend_jobs', 'sampling_calls', 'training_steps', 'statevector_evaluations'))
            or trace['source']['raw_samples_sha256'] != sha256(data['raw-samples.json']).hexdigest()
            or raw['seed'] != 20261011 or len(raw['motifs']) != 16
            or sum(len(m['tokens']) for m in raw['motifs']) != 64):
        raise ValueError('Composition source provenance mismatch')
    return json.dumps(dict(
        schema='oxfordq.composition-showcase.v1', data_status='PRE-GENERATED',
        backend_jobs_this_playback=0, freeze=freeze,
        raw_samples_text=data['raw-samples.json'].decode('utf-8'),
        trace_text=data['trace.json'].decode('utf-8'),
        media={name: base64.b64encode(contents).decode('ascii')
               for name, contents in data.items() if name.endswith(('.wav', '.mid'))},
    ))
