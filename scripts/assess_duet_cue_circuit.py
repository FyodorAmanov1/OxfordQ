"""OFFLINE feasibility only. Never imported by the production executor."""
import json
from math import log, sqrt
from types import SimpleNamespace
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit.providers import Options
from qiskit.providers.basic_provider import BasicSimulator
from qiskit_ionq.helpers import qiskit_to_ionq, decompress_metadata_string
from quantum_duet.duet_quantum import exact_outcomes, REFERENCE_ANGLES
from pathlib import Path

def local_rotations(q, cue, player, angles):
    # Ry(-theta0) then controlled Ry(theta0-theta1): own cue/angles only.
    q.ry(-float(angles[0]),player)
    q.cry(float(angles[0]-angles[1]),cue,player)

def circuit(angles,measure=False):
    # q0=a, q1=b, q2=x, q3=y; displayed classical bit order yxba.
    q=QuantumCircuit(4,4 if measure else 0,name='offline_cue_feasibility')
    q.h(0);q.cx(0,1);q.h(2);q.h(3)
    local_rotations(q,2,0,angles[:2]);local_rotations(q,3,1,angles[2:])
    if measure:q.measure(range(4),range(4))
    return q

def main():
    from unittest.mock import patch
    frozen=json.loads(Path('docs/fixtures/run-result.v1.json').read_bytes())['models']['bell_angles_radians']
    maximum=0
    for angles in (REFERENCE_ANGLES,frozen,(0.13,-0.77,1.04,2.31)):
        p=Statevector.from_instruction(circuit(angles)).probabilities()
        for x in range(2):
            for y in range(2):
                conditional=p[4*x+8*y:4*x+8*y+4]*4
                assert abs(p[4*x+8*y:4*x+8*y+4].sum()-.25)<1e-12
                analytic=np.array([(1+(-1)**((z&1)^(z>>1))*np.cos(angles[x]-angles[2+y]))/4 for z in range(4)])
                assert np.allclose(conditional,analytic,atol=1e-12,rtol=0)
                assert abs(conditional[1]+conditional[3]-.5)<1e-12
                assert abs(conditional[2]+conditional[3]-.5)<1e-12
                maximum=max(maximum,float(np.max(np.abs(conditional-exact_outcomes(angles,x,y)))))
    assert maximum<1e-12
    # Match SDK1.0.2 supported QIS basis; compiler/serializer only, no remote job.
    with patch('requests.sessions.Session.request',side_effect=AssertionError('Network forbidden')):
        # Explicit common IonQ QIS subset; decompose controlled rotations into CX/RY.
        compiled=transpile(circuit(frozen,True),basis_gates=['h','cx','ry','rz','x'],optimization_level=1)
        fake=SimpleNamespace(name='ionq_simulator',gateset=lambda:'qis',options=Options(noise_model='ideal',sampler_seed=None))
        payload=json.loads(qiskit_to_ionq(compiled,fake,{'shots':4096}))
        assert payload['type']=='ionq.circuit.v1' and payload['input']['qubits']==4
        assert decompress_metadata_string(payload['metadata']['qiskit_header'])['meas_mapped']==[0,1,2,3]
    state=Statevector.from_instruction(compiled.remove_final_measurements(inplace=False))
    assert state.equiv(Statevector.from_instruction(circuit(frozen)))
    local=BasicSimulator();job=local.run(compiled,shots=4096,seed_simulator=32003)
    counts=job.result().get_counts();groups={f'{x}{y}':{} for x in range(2) for y in range(2)}
    for yxba,n in counts.items():
        y,x,b,a=map(int,yxba)
        ba=f'{b}{a}';group=groups[f'{x}{y}'];group[ba]=group.get(ba,0)+n
    totals={xy:sum(c.values()) for xy,c in groups.items()}
    assert sum(totals.values())==4096 and min(totals.values())>0
    successes={xy:sum(n for ba,n in c.items() if (int(ba[0])^int(ba[1]))==int(xy[0])*int(xy[1]))/totals[xy] for xy,c in groups.items()}
    uniform=sum(successes.values())/4
    # Conditional independent strata, weight1/4: weighted Hoeffding sum w_i²/n_i.
    radius=sqrt(log(40)*sum(1/(16*n) for n in totals.values())/2)
    pooled=sum(successes[xy]*n for xy,n in totals.items())/4096
    print(json.dumps(dict(scope='OFFLINE statevector/local BasicSimulator/SDK1.0.2 only; no remote submission',
        conditional_max_error=maximum,bit_order='yxba: c0=a c1=b c2=x c3=y',shots=4096,
        allocation=totals,counts=groups,uniform_setting_success=uniform,pooled_success=pooled,
        uniform_conditional_95pct_hoeffding=[max(0,uniform-radius),min(1,uniform+radius)],
        gates=dict(compiled.count_ops()),serialized_gates=sorted({g['gate'] for g in payload['input']['circuit']}),serialized_type=payload['type'],job_id=job.job_id()),indent=2))

if __name__=='__main__':main()
