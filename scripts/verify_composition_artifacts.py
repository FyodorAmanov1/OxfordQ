"""Verify saved study lineage, MIDI maps, artifact hashes, audio and local links."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote
import wave

from orchestrator.composition.models import CompositionRequest, SourceBank, ComposedScore, CompositionPlan
from orchestrator.composition.compiler import validate_score, validate_plan
from orchestrator.composition.pipeline import _check_round_trip


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        self.paths.extend(value for key, value in attrs if key in ("href", "src") and value)


def verify(root):
    root = Path(root).resolve()
    studies = [root] if (root / "report.json").is_file() else sorted(root.glob("piece*"))
    checked = []
    for study in studies:
        request = CompositionRequest.model_validate_json((study / "request.json").read_text(encoding="utf-8"))
        bank = SourceBank.model_validate_json((study / "source-bank.json").read_text(encoding="utf-8"))
        report = json.loads((study / "report.json").read_text(encoding="utf-8"))
        if report["source_bank_sha256"] != bank.digest:
            raise ValueError("Saved source bank digest mismatch")
        for name, digest in report["files_sha256"].items():
            path = (study / name).resolve()
            if not path.is_relative_to(study) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Artifact hash mismatch: " + name)
        for name in report["variants"]:
            score = ComposedScore.model_validate_json((study / (name + ".score.json")).read_text(encoding="utf-8"))
            validate_score(score, bank, request)
            _check_round_trip(score, study / (name + ".mid"))
            if name != "raw":
                plan = CompositionPlan.model_validate_json((study / (name + ".plan.json")).read_text(encoding="utf-8"))
                validate_plan(plan, bank, request)
            if report["audio"]["status"] == "rendered":
                with wave.open(str(study / (name + ".wav")), "rb") as wav:
                    seconds = wav.getnframes() / wav.getframerate()
                    if seconds + .05 < score.timeline.seconds_at(score.end_tick):
                        raise ValueError("WAV truncates score timeline")
                    if wav.getsampwidth() != 2 or wav.getframerate() != report["audio"]["sample_rate"]:
                        raise ValueError("WAV format mismatch")
        checked.append(study.name)
    if not checked:
        raise ValueError("No studies found")
    for html in root.rglob("*.html"):
        parser = Links()
        parser.feed(html.read_text(encoding="utf-8"))
        for reference in parser.paths:
            url = urlsplit(reference)
            if url.scheme or url.netloc:
                raise ValueError("Listening page unexpectedly references external content")
            destination = (html.parent / unquote(url.path)).resolve()
            if not destination.is_relative_to(root) or not destination.is_file():
                raise ValueError("Missing or unsafe listening link: " + reference)
    return {"status": "passed", "studies": checked,
            "scope": "Saved source/score/MIDI/audio/hash/link checks; no browser listening or live API claims"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
