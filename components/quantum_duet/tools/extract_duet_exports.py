"""Extract Quantum Duet exports from Qollab's Console > Download output text."""
import argparse
import base64
import json
from pathlib import Path

EXPORT_FILENAMES = (
    'quantum-duet-run.json',
    'quantum-duet-quantum.mid', 'quantum-duet-classical.mid',
    'quantum-duet-raw-quantum.mid', 'quantum-duet-raw-classical.mid',
    'quantum-duet-arranged-quantum.mid', 'quantum-duet-arranged-classical.mid',
)


def extract(text, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    found = {}
    decoder = json.JSONDecoder()
    for line in text.splitlines():
        start = line.find('{"event":"duet-export"')
        if start < 0:
            continue
        record, _ = decoder.raw_decode(line[start:])
        name = record['filename']
        if name not in EXPORT_FILENAMES:
            raise ValueError('Unexpected export filename')
        if record['encoding'] == 'utf-8' and name.endswith('.json'):
            json.loads(record['payload'])
            data = record['payload'].encode('utf-8')
        elif record['encoding'] == 'base64' and name.endswith('.mid'):
            data = base64.b64decode(record['payload'], validate=True)
            if not data.startswith(b'MThd'):
                raise ValueError('Invalid MIDI header')
        else:
            raise ValueError('Unsupported export encoding')
        found[name] = data
    if not found:
        raise ValueError('No duet export envelopes found; click the export buttons before Download output')
    for name, data in found.items():
        (destination / name).write_bytes(data)
    return sorted(found)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('console_output', type=Path)
    parser.add_argument('--output-dir', type=Path, default=Path('duet-exports'))
    parser.add_argument('--filename', choices=EXPORT_FILENAMES,
                        help='Decode one payload copied from the visible Export payload field')
    args = parser.parse_args()
    text = args.console_output.read_text(encoding='utf-8-sig')
    if args.filename:
        text = json.dumps({'event': 'duet-export', 'filename': args.filename,
                           'encoding': 'utf-8' if args.filename.endswith('.json') else 'base64',
                           'payload': text.strip()}, separators=(',', ':'))
    print(json.dumps(extract(text, args.output_dir)))
