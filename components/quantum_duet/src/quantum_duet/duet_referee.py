"""Coordination-game referee. Player policies and audio never import cues here."""

import numpy as np

SETTINGS = ((0, 0), (0, 1), (1, 0), (1, 1))


def bit(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value not in (0, 1):
        raise ValueError("Expected an integer binary value")
    return int(value)


def wins(x, y, a, b):
    return (bit(a) ^ bit(b)) == (bit(x) & bit(y))


def cues(seed, rounds=16):
    """Only the referee sees this seed or complete cue sequence."""
    return np.random.default_rng(seed).integers(0, 2, (rounds, 2)).tolist()


def metrics(distributions):
    """Four rows in SETTINGS order; columns are displayed ba: 00,01,10,11."""
    p = np.asarray(distributions, dtype=float)
    if p.shape != (4, 4) or not np.isfinite(p).all() or p.min() < -1e-14:
        raise ValueError("Expected four finite nonnegative outcome distributions")
    if not np.allclose(p.sum(axis=1), 1, atol=1e-12, rtol=0):
        raise ValueError("Outcome distributions must sum to one")
    correlations = p @ np.array([1, -1, -1, 1])
    score = float(correlations @ np.array([1, 1, 1, -1]))
    successes = [float(sum(p[i, z] for z in range(4) if wins(x, y, z & 1, z >> 1)))
                 for i, (x, y) in enumerate(SETTINGS)]
    direct = float(np.mean(successes))
    if abs(direct - (0.5 + score / 8)) > 1e-12:
        raise RuntimeError("Direct success and CHSH identity disagree")
    return {"probabilities_ba": p.tolist(), "setting_success": successes,
            "correlations": correlations.tolist(), "chsh_score": score, "expected_success": direct,
            "alice_probability_one": p[:, [1, 3]].sum(axis=1).tolist(),
            "bob_probability_one": p[:, [2, 3]].sum(axis=1).tolist()}


def sampled_metrics(counts):
    if len(counts) != 4:
        raise ValueError("Require four setting count dictionaries")
    totals = [sum(c.values()) for c in counts]
    if min(totals) < 1 or len(set(totals)) != 1:
        raise ValueError("Hoeffding summary requires equal positive shot allocations")
    p = []
    for count, total in zip(counts, totals):
        if set(count) - {"00", "01", "10", "11"} or any(type(n) is not int or n < 0 for n in count.values()):
            raise ValueError("Invalid displayed-ba counts")
        p.append([count.get(format(i, "02b"), 0) / total for i in range(4)])
    result = metrics(p)
    n = sum(totals)
    delta = float(np.sqrt(np.log(40) / (2 * n)))
    estimate = result["expected_success"]
    result.update(shots_per_setting=totals[0], total_independent_shots=n,
                  interval_method="Conservative two-sided 95% Hoeffding interval",
                  interval_delta=delta, success_interval=[max(0, estimate - delta), min(1, estimate + delta)],
                  independence_assumption="Independent fresh preparations/strategy draws across all shots; fixed equal setting allocation, ideal pseudorandom simulation")
    return result
