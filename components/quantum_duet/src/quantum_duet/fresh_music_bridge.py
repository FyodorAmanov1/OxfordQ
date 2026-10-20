"""Private candidate bridge: validate measured source, then classical rules only."""
import base64
import hashlib
import json
from .fresh_qcbm import validate_source
from .five_part_composition import compose, midi_bytes


def compose_result(source_text):
    validate_source(json.loads(source_text))
    result = compose(source_text)
    midi = midi_bytes(result)
    result['export'].update(midi_base64=base64.b64encode(midi).decode('ascii'),
                            midi_sha256=hashlib.sha256(midi).hexdigest())
    return json.dumps(result, allow_nan=False)
