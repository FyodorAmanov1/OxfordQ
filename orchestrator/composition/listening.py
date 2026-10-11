"""Portable listening pages with explicitly labelled available comparisons."""
from html import escape
from pathlib import Path

CSS = "body{font:17px system-ui;background:#111827;color:#e5e7eb;max-width:900px;margin:40px auto;padding:20px}a{color:#93c5fd}article{background:#1f2937;padding:22px;border-radius:12px;margin:20px 0}audio{width:100%}small{color:#cbd5e1}table{width:100%;text-align:left}td,th{padding:8px}h1{font-size:32px}"


def _page(title, content):
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            + '<title>' + escape(title) + '</title><style>' + CSS + '</style><body>' + content + '</body></html>')


def write_study_page(out, request, report):
    title = request.style.capitalize() + " inspired ensemble study"
    content = '<h1>' + escape(title) + '</h1><p>Same frozen source bank; source pitches retained. Composer names describe inspiration.</p>'
    content += '<p><label>Playback volume <input id="volume" type="range" min="0" max="100" value="75" aria-label="Playback volume"> <span id="volume-value">75%</span></label></p>'
    for name, metrics in report["variants"].items():
        label = {"raw": "Fixed-grid source reference", "local": "Local procedural composition", "gemini": "Gemini composition"}[name]
        wav = out / (name + ".wav")
        content += '<article><h2>' + label + '</h2>'
        if report["audio"]["status"] == "rendered" and wav.is_file():
            content += '<audio controls preload="none" src="' + name + '.wav"></audio>'
        else:
            content += '<p>Audio ' + escape(report["audio"]["status"]) + '</p>'
        content += '<p><a href="' + name + '.mid">MIDI</a> · <a href="' + name + '.score.json">Score and source lineage</a></p>'
        content += '<small>' + str(metrics["seconds"]) + ' seconds · Metres ' + escape(', '.join(metrics["metres"]))
        content += ' · Ensemble span ' + str(metrics["ensemble_span_semitones"]) + ' semitones</small></article>'
    if "gemini" not in report["variants"]:
        content += '<p>Gemini: ' + escape(report["gemini"]["status"]) + '. No Gemini audio was generated.</p>'
    content += '<p>Diagnostics describe structure; they do not measure beauty. Listen for thematic return, phrasing, balance and convincing arrivals.</p>'
    content += '<p><a href="report.json">Run report</a> · <a href="source-bank.json">Immutable source bank</a> · <a href="local.plan.json">Local composition plan</a></p>'
    if report["audio"].get("performance"):
        content += '<p>Instrument-specific note envelopes shape attack, decay, breath/bow sustain and release. Track volume and phrase expression shape balance.</p>'
    content += '<script>const v=document.getElementById("volume");function volume(){document.querySelectorAll("audio").forEach(a=>a.volume=Number(v.value)/100);document.getElementById("volume-value").textContent=v.value+"%";}v.addEventListener("input",volume);volume();</script>'
    (out / "index.html").write_text(_page(title, content), encoding="utf-8")


def write_collection_page(out, studies):
    content = '<h1>Expressive ensemble studies</h1><p>Four contrasting compositions from frozen QML material. Compare the fixed-grid source with its composition.</p>'
    for name, style in studies:
        content += '<article><h2><a href="' + escape(name) + '/index.html">' + escape(name + ' — ' + style.capitalize()) + '</a></h2></article>'
    (Path(out) / "index.html").write_text(_page("Expressive ensemble studies", content), encoding="utf-8")
