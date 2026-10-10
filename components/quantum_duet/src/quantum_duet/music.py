"""Unchanged M3A local event projection; no audio dependencies."""
SCALE = (0, 2, 4, 5, 7, 9, 11)
TONICS = {"alice": 72, "bob": 48}
BPM = 120
TICKS_PER_BEAT = 480
SAMPLE_RATE = 44100
DURATION_BEATS = 0.4


def musical_event(token, output, voice, round_index):
    if type(token) is not int or token not in range(8) or type(output) is not int or output not in (0, 1):
        raise ValueError("Expected base token 0..7 and committed output 0/1")
    if voice not in TONICS or type(round_index) is not int or not 0 <= round_index < 16:
        raise ValueError("Invalid duet voice/round")
    index = token - 1 + output
    pitch = None if token == 0 else TONICS[voice] + 12 * (index // 7) + SCALE[index % 7]
    return {"round": round_index, "voice": voice, "base_token": token, "local_output": output,
            "pitch_midi": pitch, "onset_beats": round_index + output * 0.5,
            "duration_beats": DURATION_BEATS, "rest": token == 0}


def events_from_outputs(tokens, alice_outputs, bob_outputs):
    if any(len(sequence) != 16 for sequence in (tokens, alice_outputs, bob_outputs)):
        raise ValueError("Four bars require all 16 rounds, including rests and failures")
    return [musical_event(token, output, voice, i)
            for voice, outputs in (("alice", alice_outputs), ("bob", bob_outputs))
            for i, (token, output) in enumerate(zip(tokens, outputs))]

