"""Offline frozen inference; installed assets, no original research directory."""
import argparse
from pathlib import Path
from .integration import generate_take

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--shots', type=int, default=1024)
    parser.add_argument('--mode', choices=['five-live','four-recorded'], default='five-live')
    args = parser.parse_args()
    from qiskit.providers.basic_provider import BasicSimulator
    backend = BasicSimulator()
    backend.set_options(seed_simulator=32001, use_clifford_optimization=False)
    text = generate_take(backend, args.shots, args.mode, 'ideal-local-development', 32002,
                         asset_dir=Path(__file__).parent/'data')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding='utf-8')
    print('Local BasicSimulator; one batch; fixed regression seeds; saved', args.out)
    return 0
