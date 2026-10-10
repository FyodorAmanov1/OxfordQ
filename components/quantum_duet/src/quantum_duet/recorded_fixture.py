"""Qollab bridge: literal bundled files only, standard library, zero inference."""
import json
from hashlib import sha256


def load_fixture():
    with open('data/run-result.v1.json', encoding='utf-8', newline='') as f:
        raw_text = f.read()
    with open('data/qollab-local-run.json', encoding='utf-8', newline='') as f:
        source_text = f.read()
    raw = json.loads(raw_text)
    if raw['execution']['data_status'] != 'recorded' or raw['execution']['backend_run_calls_this_replay'] != 0:
        raise ValueError('Recorded fixture provenance mismatch')
    if sha256(source_text.encode('utf-8')).hexdigest() != raw['raw_source']['sha256']:
        raise ValueError('Recorded raw source byte digest mismatch')
    return json.dumps(dict(raw_envelope_text=raw_text, run_result=raw,
                          raw_source_text=source_text, playback_projection=None))
