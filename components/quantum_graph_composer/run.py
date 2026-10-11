"""Local judge entry: one BasicSimulator job, full Qiskit composition, WAV/MIDI."""
import argparse
import json
from pathlib import Path
from qiskit.providers.basic_provider import BasicSimulator
from bridge import generate
from score_writer import write_score
from audio import render


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=1201)
    parser.add_argument('--bars',type=int,default=64)
    parser.add_argument('--bpm',type=float,default=104)
    parser.add_argument('--shots',type=int,default=512)
    parser.add_argument('--interaction',type=float,default=.7)
    parser.add_argument('--out',type=Path,default=Path('output/composition'))
    args=parser.parse_args()
    print('1/3: Six-qubit entrance on Qiskit BasicSimulator; one quantum job.')
    backend=BasicSimulator(seed_simulator=args.seed)
    score=json.loads(generate(backend,args.seed,args.bars,args.bpm,args.shots,args.interaction))
    print('2/3: Persistent 13-qubit Qiskit evolution completed; rendering acoustic piano.')
    # Retain a browser-playable local take with its generated MIDI bytes.
    browser=Path(__file__).resolve().parent/'output/browser-score.json'
    browser.parent.mkdir(parents=True,exist_ok=True)
    browser.write_text(json.dumps(score,allow_nan=False),encoding='utf-8')
    score.pop('midi_base64',None)
    write_score(score,args.out)
    diagnostics=render(score,args.out.with_suffix('.wav'))
    args.out.with_suffix('.audio.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
    print('3/3: Ready:',args.out.with_suffix('.wav').resolve())
    print('MIDI:',args.out.with_suffix('.mid').resolve())
    print(json.dumps(diagnostics,indent=2))


if __name__=='__main__':
    main()
