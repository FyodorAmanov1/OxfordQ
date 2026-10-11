from __future__ import annotations
import argparse, csv, json
from pathlib import Path
import numpy as np

COARSE=["I","ii","iii","IV","V","vi","vii°","OTHER"]
RESOLVER=["V:sus","IV:min","II:dom","III:dom","bVII:maj","II:maj","V:dom","I:dom","V:min","III:maj","bVI:maj","VI:maj","VI:dom","#IV:hdim","#IV:dim","RARE_OTHER"]

p=argparse.ArgumentParser()
p.add_argument('--coarse',required=True,type=Path)
p.add_argument('--resolver',required=True,type=Path)
p.add_argument('--rare-csv',type=Path)
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'data'/'models.json')
args=p.parse_args()

def load_npz(path,qubits):
    data=np.load(path);out={}
    for i,context in enumerate(COARSE):
        key=f'theta_{i}'
        if key not in data.files: raise SystemExit(f'{path} missing {key}')
        arr=np.asarray(data[key],dtype=float)
        if arr.ndim!=1 or len(arr)==0 or len(arr)%qubits: raise SystemExit(f'Invalid {path}:{key} shape {arr.shape}')
        out[context]=arr.tolist()
    return out

coarse=load_npz(args.coarse,3);resolver=load_npz(args.resolver,4)
rare_labels=[];rare_weights=[]
if args.rare_csv and args.rare_csv.is_file():
    with args.rare_csv.open('r',encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            if int(row['rank'])<=15: continue
            rare_labels.append(row['other_class']);rare_weights.append(float(row['count']))
    total=sum(rare_weights)
    if total>0: rare_weights=[w/total for w in rare_weights]

payload={
 'schema_version':2,'coarse_contexts':COARSE,'resolver_labels':RESOLVER,
 'coarse_theta':coarse,'resolver_theta':resolver,
 'rare_labels':rare_labels,'rare_weights':rare_weights,
 'source':{'coarse':args.coarse.name,'resolver':args.resolver.name,'rare_csv':args.rare_csv.name if args.rare_csv else None,'training_scope':'POP909 major-key sections'}
}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print('Wrote',args.output)
print('Coarse depth:',len(coarse['I'])//3)
print('Resolver depth:',len(resolver['I'])//4)
print('Rare fallback labels:',len(rare_labels))
