"""Independent selected-seed rerun; exact checkpoint identity in pinned CPU environment."""
import hashlib
import json
from pathlib import Path
import time
import torch
from .data import load_examples
from .quantum import verify_equivalence
from .train import train_one


def reproduce(root):
    root = Path(root)
    report = json.loads((root / 'training/training_report.json').read_text())
    selected = next(r for r in report['results']
                    if r.get('checkpoint') == report['selected_quantum_checkpoint'])
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    verify_equivalence()
    train, _ = load_examples(root / 'data', 'train')
    validation, _ = load_examples(root / 'data', 'validation')
    destination = root / 'reproduction'
    destination.mkdir(exist_ok=True)
    _, actual, _ = train_one('qnn_full', selected['seed'], train, validation,
                            destination, selected['requested_steps'], 64,
                            time.perf_counter() + 600)
    expected = hashlib.sha256((root / 'training' / selected['checkpoint']).read_bytes()).hexdigest()
    if actual['runtime_budget_hit'] or actual['checkpoint_sha256'] != expected:
        raise AssertionError('Independent selected-checkpoint reproduction failed')
    (destination / 'report.json').write_text(json.dumps(actual, indent=2))
    print(json.dumps({'reproduced': True, 'sha256': expected,
                      'seconds': actual['training_seconds']}, indent=2))
    return actual


if __name__ == '__main__':
    import sys
    reproduce(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / 'artifacts')
