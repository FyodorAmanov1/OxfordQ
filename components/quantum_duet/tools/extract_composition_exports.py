"""Decode the optional showcase's copied payload or console export; no duet changes."""
import argparse
import base64
import json
from pathlib import Path

FILENAMES = ('oxfordq-composition-melody.mid', 'oxfordq-composition-arranged.mid', 'oxfordq-composition-provenance.json')


def extract(text, destination):
    records = []
    decoder = json.JSONDecoder()
    for line in text.splitlines():
        start = line.find('{"event":"composition-export"')
        if start >= 0:
            record, _ = decoder.raw_decode(line[start:])
            name = record['filename']
            if name not in FILENAMES:
                raise ValueError('Unexpected composition filename')
            if name.endswith('.mid') and record['encoding'] == 'base64':
                data = base64.b64decode(record['payload'], validate=True)
                if not data.startswith(b'MThd'):
                    raise ValueError('Invalid composition MIDI')
            elif name.endswith('.json') and record['encoding'] == 'utf-8':
                data = record['payload'].encode('utf-8')
                value = json.loads(data)
                if value.get('schema') != 'oxfordq.composition-provenance.v1':
                    raise ValueError('Invalid composition provenance')
            else:
                raise ValueError('Unsupported composition encoding')
            records.append((name, data))
    if not records:
        raise ValueError('No composition exports found')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in records:
        path = destination / name
        if path.exists():
            raise ValueError('Export destination already exists; preserve existing files')
        path.write_bytes(data)
    return [name for name, _ in records]


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--filename', choices=FILENAMES)
    p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args()
    text = a.input.read_text(encoding='utf-8-sig')
    if a.filename:
        text = json.dumps(dict(event='composition-export', filename=a.filename,
                              encoding='base64' if a.filename.endswith('.mid') else 'utf-8', payload=text.strip()), separators=(',', ':'))
    print(extract(text, a.output_dir))
