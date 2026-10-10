"""Coordinator seam acceptance: real rules output, exact source bytes, no inference."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from quantum_duet.browser_projection import project, arrange_browser, browser_bundle
from quantum_duet.orchestration_adapter import freeze_result, arrange_result

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT/'docs/fixtures/run-result.v1.json').read_bytes()
SOURCE = (ROOT/'components/quantum_duet/tests/fixtures/qollab-local-run.json').read_bytes()

@pytest.fixture(scope='module')
def outcomes():
    frozen=freeze_result(json.loads(RAW),raw_bytes=SOURCE)
    with patch('quantum_duet.integration.generate_take',side_effect=AssertionError('New submission')), \
         patch('qiskit.providers.basic_provider.BasicSimulator.run',side_effect=AssertionError('New job')):
        return {p:arrange_result(frozen,policy=p).to_dict() for p in ('quantum','classical')}

def test_success_ticks_rests_identity_and_immutable_source(outcomes):
    before=deepcopy(outcomes)
    p=project(RAW,outcomes,raw_source_bytes=SOURCE)
    assert p['available'] and p['raw_envelope_sha256']==sha256(RAW).hexdigest()
    assert p['raw_source']['sha256']==sha256(SOURCE).hexdigest()
    assert outcomes==before
    raw=json.loads(RAW)
    for policy in ('quantum','classical'):
        events=p['policies'][policy]['events']
        assert len(events)==32
        for part in outcomes[policy]['arranged']['output_parts']:
            for n in part['notes']:
                e=next(e for e in events if e.get('output_id')==n['id'])
                assert e['onset_beats']*480==n['onset_tick']
                assert e['duration_beats']*480==n['duration_ticks']
                assert e['rest']==n['muted'] and e['run_id']==raw['run_id']
        assert {e['source_event_ids'][0] for e in events}=={e['event_id'] for e in raw['events'][policy]}
        assert sum(e['rest'] for e in events)>=sum(e['rest'] for e in raw['events'][policy])
    bundle=browser_bundle(RAW,p,raw_source_bytes=SOURCE)
    assert bundle['raw_envelope_text'].encode()==RAW
    assert bundle['raw_source_text'].encode()==SOURCE
    assert bundle['run_result']==raw and bundle['run_result']['arranged'] is None

def test_failed_policy_keeps_raw_and_other_policy(outcomes):
    with patch('orchestrator.pipeline.orchestrate',side_effect=RuntimeError('sensitive-path')):
        failed=arrange_result(freeze_result(json.loads(RAW),raw_bytes=SOURCE),policy='quantum').to_dict()
    p=project(RAW,dict(outcomes,quantum=failed))
    assert not p['available'] and not p['policies']['quantum']['events']
    assert len(p['policies']['classical']['events'])==32
    assert browser_bundle(RAW,p)['raw_envelope_text'].encode()==RAW
    assert 'sensitive-path' not in json.dumps(p)

def test_muted_note_is_retained_as_silent_with_lineage(outcomes):
    changed=deepcopy(outcomes)
    a=changed['quantum']['arranged'];n=a['output_parts'][1]['notes'][0]
    n['muted']=True
    next(l for l in a['lineage'] if l['output_id']==n['id'])['muted']=True
    e=next(e for e in project(RAW,changed)['policies']['quantum']['events'] if e.get('output_id')==n['id'])
    assert e['muted'] and e['rest'] and e['pitch_midi'] is None
    assert e['source_event_ids'] and e['round_id']

@pytest.mark.parametrize('mutation', [
    lambda o:o['quantum']['events']['quantum'][0].update(velocity=12),
    lambda o:o['quantum']['arranged'].update(policy='classical'),
    lambda o:o['quantum']['arranged'].update(raw_result_canonical_json_sha256='0'*64),
    lambda o:o['quantum']['arranged']['output_parts'][0]['notes'][0].update(duration_ticks=0),
    lambda o:o['quantum']['arranged']['lineage'][0].update(event_id='unknown'),
    lambda o:o['quantum']['arranged'].update(backend_actual='another-provider'),
    lambda o:o['quantum']['arranged']['lineage'].pop(),
    lambda o:(o['quantum']['arranged']['output_parts'][0]['notes'][0].update(source_id='alice:n99'),
              o['quantum']['arranged']['lineage'][0].update(source_id='alice:n99')),
    lambda o:o['quantum']['arranged']['output_parts'][0]['notes'][0].update(onset_tick=True),
    lambda o:o['quantum']['arranged']['transformation_ids'].append('unlinked'),
])
def test_rejects_contradictory_projection_inputs(outcomes,mutation):
    changed=deepcopy(outcomes);mutation(changed)
    with pytest.raises((ValueError,KeyError)): project(RAW,changed)

def test_exact_source_digest_and_zero_new_jobs():
    with pytest.raises(ValueError,match='byte digest'): browser_bundle(RAW,raw_source_bytes=SOURCE+b' ')
    with patch('qiskit.providers.basic_provider.BasicSimulator.run',side_effect=AssertionError('New job')):
        bundle=arrange_browser(RAW,raw_source_bytes=SOURCE)
    assert bundle['run_result']['execution']['backend_run_calls_this_replay']==0
    assert bundle['playback_projection']['available']
