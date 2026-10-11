"""Physics and end-to-end contracts; no claim to measure musical quality."""
import json
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from qiskit import QuantumCircuit
from qiskit.circuit.library import DiagonalGate
from qiskit.providers.basic_provider import BasicSimulator
from qiskit.quantum_info import Statevector
from quantum_engine import QiskitDynamics, entrance_circuit, run_entrance
from graph import MusicalGraph, tilt_to_mean
from composer import compose
from bridge import load_piano


class CountingSimulator:
    def __init__(self, seed=1201):
        self.inner=BasicSimulator(seed_simulator=seed);self.calls=0
    def __getattr__(self,name):return getattr(self.inner,name)
    def run(self,*args,**kwargs):
        self.calls+=1;return self.inner.run(*args,**kwargs)


class Tests(unittest.TestCase):
    def test_entire_evolution_matches_independent_qiskit_circuit(self):
        g=MusicalGraph(8);psi=g.initial(1201);random=np.random.default_rng(5)
        feedback=np.broadcast_to(random.uniform(0,.2,(64,1,8)),(64,8,8)).copy()
        v=.7*g.interaction+feedback.reshape(g.shape);dt=.55/4
        circuit=QuantumCircuit(12)
        bits=([10,11],[8,9],[6,7],[3,4,5],[0,1,2])
        ch=v.reshape(64,8,8)[:,0,:]
        cr=v.reshape(64,8,8)[:,:,0]-v.reshape(64,8,8)[:,0,0,None]
        for _ in range(4):
            for side in range(2):
                circuit.append(DiagonalGate(np.exp(-.5j*dt*ch).ravel()),list(bits[-1])+[6,7,8,9,10,11])
                circuit.append(DiagonalGate(np.exp(-.5j*dt*cr).ravel()),list(bits[-2])+[6,7,8,9,10,11])
                if side==0:
                    for u,q in zip(g.gates(.55,4),bits):circuit.unitary(u,q)
        independent=Statevector(psi.ravel()).evolve(circuit).data
        efficient=QiskitDynamics().step(g,psi,.55,.7,feedback,4).ravel()
        self.assertLess(np.max(abs(independent-efficient)),1e-11)

    def test_phase_memory_changes_future_probabilities(self):
        g=MusicalGraph();a=g.initial(1201);b=a*np.exp(2.5j*g.interaction)
        self.assertLess(np.sum(abs(abs(a)**2-abs(b)**2))/2,1e-14)
        engine=QiskitDynamics();zero=np.zeros(g.shape)
        aa=engine.step(g,a,.58,.7,zero,64);bb=engine.step(g,b,.58,.7,zero,64)
        self.assertGreater(np.sum(abs(abs(aa)**2-abs(bb)**2))/2,.01)

    def test_one_job_and_reproducible_music(self):
        backend=CountingSimulator();prior,execution=run_entrance(backend,1201,128,.7)
        self.assertEqual(backend.calls,1);self.assertEqual(execution['backend_run_calls'],1)
        self.assertEqual(sum(execution['counts'].values()),128)
        self.assertAlmostEqual(prior.sum(),1)
        a=compose(1201,16,contour_prior=prior,engine=QiskitDynamics())
        b=compose(1201,16,contour_prior=prior,engine=QiskitDynamics())
        self.assertEqual(a['events'],b['events']);self.assertEqual(len(a['theme']),4)
        self.assertEqual(len(a['decisions']),16);self.assertEqual(sum(s['bars'] for s in a['form']),16)
        self.assertLess(a['metadata']['maximum_state_norm_error'],1e-9)
        for event in a['events']:
            self.assertTrue(0<=event['pitch']<=127);self.assertGreater(event['duration_beats'],0)
        self.assertEqual(a['decisions'][-1]['node']['harmony'],0)
        self.assertEqual(a['decisions'][-1]['lead_pitches'],[a['metadata']['tonic_pc']+72]*4)
        json.dumps(a,allow_nan=False)

    def test_entrance_interaction_changes_joint_law(self):
        a=Statevector.from_instruction(entrance_circuit(1201,0,False)).probabilities()
        b=Statevector.from_instruction(entrance_circuit(1201,.7,False)).probabilities()
        self.assertGreater(np.sum(abs(a-b))/2,.01)

    def test_semantic_actuator_preserves_hard_support(self):
        q,report=tilt_to_mean(np.array([.2,.3,.5,0]),np.array([0,.3,.8,1]),.4)
        self.assertEqual(q[-1],0);self.assertAlmostEqual(report['expected'],.4,places=10)

    def test_piano_bank_portable_and_licensed(self):
        bank=json.loads(load_piano());self.assertEqual(len(bank['regions']),10)
        self.assertEqual(bank['source_sha256'],'f4f69027c04e8f1e0b87ee7ffad254d133ca8e07740844ea14307821a1dbb221')
        for pitch in range(128):
            self.assertEqual(sum(r['low']<=pitch<=r['high'] for r in bank['regions']),1)

    def test_no_hidden_backend_fallback(self):
        class Failed(CountingSimulator):
            def run(self,*args,**kwargs):self.calls+=1;raise RuntimeError('provider failure')
        backend=Failed()
        with self.assertRaisesRegex(RuntimeError,'provider failure'):run_entrance(backend,1201,128,.7)
        self.assertEqual(backend.calls,1)


if __name__=='__main__':unittest.main()
