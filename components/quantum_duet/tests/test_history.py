"""Recompute the retained historical result; makes no backend submission."""
import json, math
from pathlib import Path

def test_frozen_platform_counts_and_model_provenance():
    root=Path(__file__).resolve().parents[1]
    take=json.loads((root/'tests/fixtures/qollab-local-run.json').read_text())
    groups=take['execution']['experiments'][:4]
    successes=0
    for row in groups:
        x,y=row['setting']
        assert sum(row['counts'].values())==1024
        successes+=sum(n for bits,n in row['counts'].items() if (int(bits[0])^int(bits[1]))==(x&y))
    assert successes/4096==take['statistics']['expected_success']==0.85888671875
    delta=math.sqrt(math.log(40)/(2*4096))
    assert take['statistics']['success_interval']==[successes/4096-delta,successes/4096+delta]
    assets=root/'src/quantum_duet/data'
    bell=json.loads((assets/'selected_angles.json').read_text())
    melody=json.loads((assets/'melody_angles.json').read_text())
    assert take['models']['bell_angles_radians']==bell['parameters_radians']
    assert take['models']['bell_checkpoint_sha256']==bell['source_sha256']
    assert take['models']['qcbm_checkpoint_sha256']==melody['source_checkpoint_sha256']
    assert take['execution']['job_id']=='f788ed00-3823-4ae3-ab34-0131a4e7c744'
