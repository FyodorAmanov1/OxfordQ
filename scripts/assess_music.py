"""Write a listening comparison and compact, explicitly heuristic assessment."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    directory = args.directory.resolve()
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    score = json.loads((directory / "arrangement.json").read_text(encoding="utf-8"))
    assessment = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Symbolic comparison; listening ratings are not yet collected",
        "backend_requested": report["backend_requested"],
        "provider_status": report["provider_status"],
        "lead_preserved": report["lead_preserved"],
        "hard_validation_errors": report["hard_validation_errors"],
        "warnings": report["warnings"],
        "metrics": report["metrics"],
        "parts": [{"id": part["id"], "instrument": part["instrument"],
                   "source_notes": len(part["notes"]),
                   "active_notes": sum(not note["muted"] for note in part["notes"])}
                  for part in score["parts"]],
        "audio": report["audio"],
        "listening_questions": [
            "Can you recognize each source motif after arrangement?",
            "Is the lead audible against the accompanying instruments?",
            "Do phrase changes and cadences sound intentional?",
            "Do clashes sound expressive or accidental?",
            "Would you prefer this version to the independent parts?"],
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(directory.glob("*")) if p.suffix in (".mid", ".wav")},
    }
    (directory / "assessment.json").write_text(json.dumps(assessment, indent=2), encoding="utf-8")
    rows, players = [], []
    for name in ("original", "baseline", "arrangement"):
        metrics = report["metrics"][name]
        rows.append("<tr><th>" + name + "</th>" + "".join("<td>" + str(metrics[k]) + "</td>"
                    for k in ("heuristic_score", "harmonic_fit_with_ornaments",
                              "accompaniment_note_retention", "rough_interval_ratio")) + "</tr>")
        audio = '<audio controls preload="none" src="' + name + '.wav"></audio>' if (directory / (name + ".wav")).exists() else "<p>Audio not rendered.</p>"
        players.append("<section><h2>" + name.title() + "</h2>" + audio + '<p><a href="' +
                       name + '.mid">Download MIDI</a></p></section>')
    text = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Music arrangement comparison</title>
<style>body{font:17px system-ui;max-width:950px;margin:40px auto;padding:0 20px;background:#f8f6ef;color:#242c36}
section{display:inline-block;padding:20px;margin:10px;background:white;border-radius:12px}
audio{max-width:100%}table{border-collapse:collapse;width:100%}th,td{padding:12px;border-bottom:1px solid #bbb;text-align:left}</style>
<h1>Music arrangement comparison</h1>
<p>Independent QCBM sequences decoded for each instrument, then reconciled with POP909 harmony.
Scores below are symbolic heuristics. They do not establish perceived musical quality.
With the rules backend, baseline and arrangement are the same result.</p>"""
    text += "".join(players) + "<h2>Symbolic comparison</h2><table><tr><th>Version</th><th>Heuristic</th><th>Harmonic fit</th><th>Retention</th><th>Rough intervals</th></tr>" + "".join(rows) + "</table>"
    text += "<h2>Listening review</h2><ul>" + "".join("<li>" + html.escape(q) + "</li>" for q in assessment["listening_questions"]) + "</ul>"
    text += "<p>Provider: " + html.escape(report["provider_status"]) + ". Lead preserved: " + str(report["lead_preserved"]) + '.</p><a href="assessment.json">Assessment and file hashes</a></html>'
    (directory / "comparison.html").write_text(text, encoding="utf-8")
    print(json.dumps({"assessment": str(directory / "assessment.json"),
                      "comparison": str(directory / "comparison.html")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
