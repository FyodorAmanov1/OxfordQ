"""Standalone checks in the actual deployment working directory."""
import copy
import importlib.util
import json
import sys
import unittest
from collections import Counter
from pathlib import Path
from qiskit.providers.basic_provider import BasicSimulator

sys.path.insert(0, str(Path.cwd()))
from quantum_duet.integration import generate_take, assemble_take, load_assets, reconstructed
from quantum_duet.duet_referee import SETTINGS
from quantum_duet.duet_quantum import run_batch, decode_outcome
from quantum_duet.music import events_from_outputs, musical_event
import numpy as np

class Backend(BasicSimulator):
    def __init__(self, *, reverse=False, corrupt=False):
        super().__init__()
        self.calls = 0
        self.reverse, self.corrupt = reverse, corrupt
        self.set_options(seed_simulator=32001, use_clifford_optimization=False)
    def run(self, *args, **kwargs):
        self.calls += 1
        job = super().run(*args, **kwargs)
        result = job.result()
        if self.reverse:
            result.results.reverse()
        if self.corrupt:
            result.results[0].header['name'] = 'unknown-result'
        return job

class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = Backend()
        cls.take = json.loads(generate_take(cls.backend, 1024, 'five-live', 'ideal-local-development', 32002))

    def test_one_complete_job_and_allocation(self):
        t = self.take
        self.assertEqual(self.backend.calls, 1)
        self.assertEqual(t['execution']['circuit_count'], 5)
        self.assertEqual(t['statistics']['total_independent_shots'], 4096)
        self.assertTrue(t['base_melody']['generated_now'])
        for row in t['execution']['experiments']:
            self.assertEqual(sum(row['counts'].values()), 1024)
        self.assertFalse(any(m in sys.modules for m in ('music21','mido','quantum_duet.duet_training','quantum_duet.data_selection')))

    def test_result_names_survive_permutation(self):
        b = Backend(reverse=True)
        take = json.loads(generate_take(b, 32, 'four-recorded', 'ideal-local-development', 32002))
        self.assertEqual(b.calls, 1)
        self.assertEqual([r['result_index'] for r in take['execution']['experiments']], [3,2,1,0])
        self.assertEqual([r['setting'] for r in take['execution']['experiments']], [list(s) for s in SETTINGS])
        self.assertFalse(take['base_melody']['generated_now'])
        self.assertIn('recorded', take['base_melody']['origin'].lower())

    def test_unknown_label_fails_without_retry(self):
        b = Backend(corrupt=True)
        with self.assertRaisesRegex(RuntimeError, 'labels differ'):
            generate_take(b, 32, 'four-recorded', 'ideal-local-development', 32002)
        self.assertEqual(b.calls, 1)

    def test_unsupported_provider_result_is_explicit_failure(self):
        from types import SimpleNamespace
        class Unsupported(Backend):
            def run(self, *args, **kwargs):
                super().run(*args, **kwargs)
                return SimpleNamespace(result=lambda: {'histograms': []})
        b=Unsupported()
        with self.assertRaisesRegex(RuntimeError, 'Unsupported provider result representation'):
            generate_take(b,32,'four-recorded','ideal-local-development',32002)
        self.assertEqual(b.calls,1)

    def test_limits_and_options_prevent_submission(self):
        b = Backend()
        for shots in (0, 15, 4097, True, 1.5):
            with self.assertRaises(ValueError): generate_take(b, shots)
        self.assertEqual(b.calls, 0)
        b.options.set_validator('shots',(16,64))
        with self.assertRaises(ValueError): generate_take(b,1024)
        self.assertEqual(b.calls,0)

    def test_bit_order_and_melody_decode(self):
        self.assertEqual(decode_outcome('01'), (1,0))
        self.assertEqual(decode_outcome('10'), (0,1))
        for bits, motif in zip(self.take['base_melody']['sampled_bitstrings'], self.take['base_melody']['motifs']):
            self.assertEqual(motif, [int(bits[12-3*i-3:12-3*i], 2) for i in range(4)])
        for r in self.take['rounds']['quantum']:
            self.assertEqual(r['displayed_ba'], f"{r['b']}{r['a']}")

    def test_statistics_recomputed_from_all_counts(self):
        groups = self.take['execution']['experiments'][:4]
        successes = [sum(n for bits,n in row['counts'].items() if (int(bits[0]) ^ int(bits[1])) == (x & y))
                     for (x,y),row in zip(SETTINGS,groups)]
        estimate = sum(successes)/4096
        self.assertEqual(self.take['statistics']['expected_success'], estimate)
        delta = np.sqrt(np.log(40)/(2*4096))
        np.testing.assert_allclose(self.take['statistics']['success_interval'], [estimate-delta, estimate+delta])

    def test_local_music_remote_input_invariance(self):
        for name in ('quantum','classical'):
            original = self.take['rounds'][name]
            remote = copy.deepcopy(original)
            for row in remote:
                row['y'] ^= 1; row['b'] ^= 1; row['win'] = not row['win']
            for before, after in zip(original, remote):
                self.assertEqual(musical_event(before['base_token'],before['a'],'alice',before['round']),
                                 musical_event(after['base_token'],after['a'],'alice',after['round']))
            remote = copy.deepcopy(original)
            for row in remote:
                row['x'] ^= 1; row['a'] ^= 1; row['win'] = not row['win']
            for before, after in zip(original, remote):
                self.assertEqual(musical_event(before['base_token'],before['b'],'bob',before['round']),
                                 musical_event(after['base_token'],after['b'],'bob',after['round']))
        reference = json.loads((Path(__file__).parent/'fixtures/music-reference.json').read_text())
        for event in reference['events']:
            self.assertEqual(musical_event(event['base_token'],event['local_output'],event['voice'],0),event)

    def test_shared_randomness_is_independent_of_remote_cues(self):
        from quantum_duet.duet_classical import alice_output, bob_output
        for row in self.take['rounds']['classical']:
            strategy = row['shared_strategy']
            for remote in (0,1):
                self.assertEqual(alice_output(row['x'],strategy[:2]),row['a'])
                self.assertEqual(bob_output(row['y'],strategy[2:]),row['b'])
        self.assertNotEqual(self.take['randomness']['shared_strategy_seed'], self.take['randomness']['referee_cue_seed'])

    def test_reconstructed_order_preserves_full_multiset_and_shot_count(self):
        count = {'00':8, '01':4, '10':3, '11':1}
        first = reconstructed(count,np.random.default_rng(1))
        second = reconstructed(count,np.random.default_rng(2))
        self.assertEqual(Counter(first), count)
        self.assertEqual(Counter(second), count)
        self.assertNotEqual(first,second)
        before = copy.deepcopy(self.take['statistics'])
        for seed in range(10):
            angles,melody,recorded = load_assets()
            take = assemble_take(self.take['execution'], angles, melody, recorded, 'five-live', 'ideal-local-development', seed)
            self.assertEqual(take['statistics'],before)

if __name__ == '__main__':
    unittest.main(verbosity=2)
