"""Render the text export if a Qollab embedded-frame download was blocked."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audio import render
from score_writer import write_score

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score',type=Path)
    parser.add_argument('--out',type=Path,default=Path('output/exported'))
    args=parser.parse_args();score=json.loads(args.score.read_text(encoding='utf-8'))
    score.pop('midi_base64',None)
    write_score(score,args.out)
    print(json.dumps(render(score,args.out.with_suffix('.wav')),indent=2))
