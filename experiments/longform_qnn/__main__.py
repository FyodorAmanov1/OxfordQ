import argparse
import json
from pathlib import Path
from .data import prepare,load_examples
from .train import run,load_checkpoint
from .generate import export_example

def main():
    parser=argparse.ArgumentParser(description='Offline isolated long-form QNN experiment')
    parser.add_argument('command',choices=['prepare','train','generate','equivalence'])
    parser.add_argument('--artifacts',type=Path,default=Path(__file__).parent/'artifacts')
    parser.add_argument('--steps',type=int,default=320)
    parser.add_argument('--seeds',type=int,nargs='+',default=[11,22,33])
    parser.add_argument('--budget-seconds',type=int,default=1800)
    parser.add_argument('--prior-test-sources',type=Path)
    args=parser.parse_args();root=args.artifacts
    if args.command=='prepare':prepare(root/'data',args.prior_test_sources)
    elif args.command=='train':run(root/'data',root/'training',args.steps,args.seeds,args.budget_seconds)
    elif args.command=='equivalence':
        from .quantum import verify_equivalence
        print(json.dumps(verify_equivalence(),indent=2))
    else:
        report=json.loads((root/'training/training_report.json').read_text())
        checkpoint=root/'training'/report['selected_quantum_checkpoint'];model,_=load_checkpoint(checkpoint)
        _,pieces=load_examples(root/'data','train')
        for name,seed,form in [('free',101,False),('structured',202,True)]:
            trace=export_example(model,checkpoint,seed,root/'examples'/name,pieces,form)
            print(json.dumps(dict(example=name,diagnostics=trace['diagnostics'],audio=trace['audio'],inference_seconds=trace['inference_seconds']),indent=2))

if __name__=='__main__':main()
