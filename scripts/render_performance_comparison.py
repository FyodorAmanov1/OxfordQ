"""Render one existing phrase three ways, without generator or provider calls."""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import numpy as np
from orchestrator.models import OrchestrationConfig
from orchestrator.audio import discover_audio, _write_pcm
from orchestrator.articulated_audio import render_score as legacy_render
from orchestrator.acoustic_audio import render_acoustic
from orchestrator.composition.models import ComposedScore, MusicalTimeline
from orchestrator.composition.performer import RulePerformer
from orchestrator.composition.midi import export_performed_midi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--style", choices=["bach","mozart","debussy","rachmaninoff"],default="mozart")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bars", type=int, default=4)
    parser.add_argument("--sample-library", type=Path)
    parser.add_argument("--sfizz-library", type=Path)
    parser.add_argument("--fluidsynth")
    parser.add_argument("--soundfont", type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Choose a fresh output directory")
    original = ComposedScore.model_validate_json(args.score.read_text(encoding="utf-8"))
    if not 1 <= args.bars <= original.bars:
        parser.error("Excerpt bars must fit the score")
    score = original.model_copy(deep=True)
    bars = score.timeline.bars[:args.bars]
    end = score.timeline.bar_starts[args.bars] if args.bars<score.bars else score.end_tick
    score.timeline = MusicalTimeline(ppq=score.ppq,bars=bars,tempos=[t for t in score.timeline.tempos if t.tick<end])
    for part in score.parts:
        part.notes = [n for n in part.notes if n.onset_tick<end]
        for note in part.notes:
            note.duration_ticks = min(note.duration_ticks,end-note.onset_tick)
        part.expression = [(t,v) for t,v in part.expression if t<end]
    score.phrases = [p for p in score.phrases if p.start_tick<end]
    for phrase in score.phrases:
        phrase.end_tick = min(end,phrase.end_tick)
        phrase.peak_tick = min(phrase.peak_tick,phrase.end_tick-1)
    occurrences = []
    for occurrence in score.occurrences:
        slots = [s for s in occurrence["events"] if s["onset_tick"]<end]
        if not slots:
            continue
        occurrence["events"] = slots
        for slot in slots:
            slot["duration_ticks"] = min(slot["duration_ticks"],end-slot["onset_tick"])
        occurrences.append(occurrence)
    score.occurrences = occurrences
    config = OrchestrationConfig(sample_library=args.sample_library,sfizz_library=args.sfizz_library,
        fluidsynth=args.fluidsynth,soundfont=args.soundfont,audio_renderer="sfizz")
    executable,font = discover_audio(config)
    if not executable or not font or not font.is_file():
        parser.error("The old-envelope comparison also requires FluidSynth and --soundfont")
    args.out.mkdir(parents=True)
    score_path = args.out/"phrase.score.json"
    score_path.write_text(score.model_dump_json(indent=2),encoding="utf-8")
    old,old_info = legacy_render(score,executable,font,config.sample_rate)
    performer = RulePerformer()
    native = performer.perform(score,style=args.style,seed=42,strength=0)
    expressive = performer.perform(score,style=args.style,seed=42,strength=.6)
    plain,_,plain_info = render_acoustic(score,native,config)
    played,_,played_info = render_acoustic(score,expressive,config)
    signals = {"old_envelopes":old,"acoustic_native":plain,"acoustic_expressive":played}
    gains = {}
    for name,data in signals.items():
        audible = np.max(np.abs(data),axis=1)>.0005
        rms = np.sqrt(np.mean(data[audible]**2)) if audible.any() else 0
        if not rms:
            raise RuntimeError("Silent phrase: "+name)
        gains[name] = .1/float(rms)
    peak = max(float(np.max(np.abs(data)))*gains[name] for name,data in signals.items())
    headroom = min(1,10**(-1/20)/peak)
    for name,data in signals.items():
        _write_pcm(args.out/(name+".wav"),data*gains[name]*headroom,(2,2,config.sample_rate))
    for name,plan in [("acoustic_native",native),("acoustic_expressive",expressive)]:
        (args.out/(name+".performance.json")).write_text(plan.model_dump_json(indent=2),encoding="utf-8")
        export_performed_midi(score,plan,args.out/(name+".mid"))
    labels = [("old_envelopes","Previous isolated-note envelopes"),("acoustic_native","Acoustic samples, native envelopes"),
              ("acoustic_expressive","Same acoustic samples, expressive performance")]
    page = '<!doctype html><meta charset="utf-8"><title>Same phrase, three performances</title><style>body{font:18px system-ui;max-width:850px;margin:40px auto;padding:20px;background:#111827;color:#eee}audio{width:100%}a{color:#93c5fd}</style><h1>Same phrase, three performances</h1><p>Identical source notes and pitches. Constant loudness matching preserves each performance’s internal dynamics. Both acoustic versions use the same room setting.</p>'
    for name,label in labels:
        page += '<h2>'+escape(label)+'</h2><audio controls preload="none" src="'+name+'.wav"></audio>'
    page += '<p><a href="phrase.score.json">Logical phrase</a> · <a href="report.json">Rendering report</a></p><p>Connected sustain approximates legato; this library does not contain recorded interval transitions.</p>'
    page += '<script>const players=[...document.querySelectorAll("audio")];players.forEach(a=>a.addEventListener("play",()=>players.forEach(b=>{if(a!==b)b.pause();})));</script>'
    (args.out/"index.html").write_text(page,encoding="utf-8")
    report = {"input_score_sha256":hashlib.sha256(args.score.read_bytes()).hexdigest(),"bars":args.bars,
        "variants":{"old":old_info,"native":plain_info,"expressive":played_info},
        "normalization":"Constant audible RMS matching; shared -1 dBFS headroom, not LUFS",
        "generator_calls":0,"provider_calls":0,"listening_assessment":"Requires human listening"}
    (args.out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Phrase comparison:",args.out/"index.html")


if __name__=="__main__":
    main()
