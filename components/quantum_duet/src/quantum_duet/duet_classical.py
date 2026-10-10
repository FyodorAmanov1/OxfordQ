"""Local classical policies, exhaustive strategies and cue-independent randomness."""

from itertools import product

import numpy as np

from .duet_referee import SETTINGS, bit, metrics, wins


def alice_output(x, local_function):
    if len(local_function) != 2:
        raise ValueError("Alice receives only her two-entry local function")
    return bit(local_function[bit(x)])


def bob_output(y, local_function):
    if len(local_function) != 2:
        raise ValueError("Bob receives only his two-entry local function")
    return bit(local_function[bit(y)])


def strategy_table():
    rows = []
    for strategy in product((0, 1), repeat=4):
        outcomes = [(alice_output(x, strategy[:2]), bob_output(y, strategy[2:])) for x, y in SETTINGS]
        success = [wins(x, y, a, b) for (x, y), (a, b) in zip(SETTINGS, outcomes)]
        rows.append({"strategy": list(strategy), "outcomes_ab": [list(v) for v in outcomes],
                     "setting_wins": success, "expected_success": float(np.mean(success))})
    return rows


def maximizing_strategies():
    rows = strategy_table()
    maximum = max(r["expected_success"] for r in rows)
    return [r["strategy"] for r in rows if r["expected_success"] == maximum]


def shared_choices(seed, rounds):
    """No cues or referee seed are accepted; prepare choices before cues arrive."""
    strategies = maximizing_strategies()
    indices = np.random.default_rng(seed).integers(0, len(strategies), rounds).tolist()
    return indices, [strategies[i] for i in indices]


def mixture_metrics():
    strategies = maximizing_strategies()
    p = np.zeros((4, 4))
    for i, (x, y) in enumerate(SETTINGS):
        for strategy in strategies:
            a, b = alice_output(x, strategy[:2]), bob_output(y, strategy[2:])
            p[i, a + 2 * b] += 1 / len(strategies)
    return metrics(p)


def centralized_metrics():
    """Communication restriction removed; never supplied to a local player."""
    p = np.zeros((4, 4))
    for i, (x, y) in enumerate(SETTINGS):
        p[i, 2 * (x & y)] = 1
    return {"label": "Centralized classical: communication restriction removed", **metrics(p)}
