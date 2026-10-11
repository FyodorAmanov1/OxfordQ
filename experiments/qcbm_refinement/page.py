"""Two versions, two textures; no platform hooks or external dependencies."""
import html
import json


def write_page(out, trace, analysis):
    players = ''
    for version,label in [('original','Original PR #8 — unchanged'),('improved','Fully refined — classical development')]:
        players += f'<section><h2>{label}</h2>'
        for texture in ('melody','arranged'):
            stem = f'{version}-{texture}'
            players += f'<div data-texture="{texture}"'+(' hidden' if texture=='arranged' else '')+f'><audio controls preload="metadata" src="{stem}.wav" aria-label="{label}, {texture}"></audio><p><a href="{stem}.mid" download="{stem}.mid">Download {texture} MIDI</a></p></div>'
        players += '</section>'
    rows = ''
    fields = ('accented_duration_chord_tone_fraction','sustained_nonchord_semitone_overlap_note_beats',
        'mean_abs_melody_interval','rhythm_patterns','distinct_velocities','mean_abs_bass_interval',
        'mean_chord_nearest_voice_motion','A_reprise_pitch_class_agreement')
    for key in fields:
        cells = [analysis[v][key] for v in ('original','improved')]
        rows += '<tr><th>'+key.replace('_',' ')+'</th>'+''.join('<td>'+html.escape(str(round(x,3) if isinstance(x,float) else x))+'</td>' for x in cells)+'</tr>'
    source = trace['source']
    provenance = json.dumps(trace,indent=2).replace('<','\\u003c')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OxfordQ — original and refined composition</title>
<style>body{font:17px system-ui;max-width:1000px;margin:32px auto;padding:0 22px;background:#f7f5ef;color:#26362f}h1{font-size:30px}h2{font-size:21px}section{background:white;border-radius:10px;padding:18px;margin:20px 0}audio{width:100%}p{line-height:1.5}label{font-weight:600}select{font:inherit;padding:7px;margin:0 8px}table{border-collapse:collapse;font-size:14px}th,td{text-align:left;border:1px solid #b9bfb7;padding:8px}textarea{box-sizing:border-box;width:100%;min-height:180px;font:12px monospace}[hidden]{display:none}.tag{font-weight:700;color:#385642}a{color:#284f82}</style>
<h1>One preserved quantum source, two classical compositions</h1>
<p class="tag">PRE-GENERATED · 16 bars · 120 BPM · 32 seconds · A–A′–B–A″</p>
<p>Both versions reuse the same sixteen frozen-QCBM motifs, seed 20261011. This refinement performs no sampling, training or backend jobs. It changes classical harmony, timing, register, dynamics and four phrase endings. It is not a CHSH experiment or execution on a selected Qollab backend.</p>
<p>The original MIDI/WAV files are byte-identical to PR #8. Both versions use its additive synthesizer and instrumentation. Refined WAVs have one documented gain adjustment to match reference RMS; MIDI dynamics remain expressive.</p>
<label for="texture">Listening texture</label><select id="texture"><option value="melody">Melody only</option><option value="arranged">With bass and chords</option></select>
<p>Play either version; the previous player pauses automatically. The native timeline supports seeking when served with HTTP byte ranges.</p>'''
    page += players + '<h2>Objective diagnostics — no automatic winner</h2><table><tr><th>Diagnostic</th><th>Original</th><th>Refined</th></tr>'+rows+'</table>'
    page += '<p>These rule-based diagnostics do not establish audible superiority. Seventh chords change chord membership; smooth motion is not always desirable. <strong>Subjective quality: pending your listening assessment.</strong></p>'
    page += '<h2>Source provenance</h2><p>Preserved raw SHA-256: <code>'+source['raw_samples_sha256']+'</code></p>'
    page += '<p>Checkpoint identity: <code>'+source['original_checkpoint_sha256']+'</code>. Original seed, bitstrings, probabilities and all 64 tokens are preserved. Each refinement and accompaniment event records its source identities.</p>'
    page += '<details><summary>Read complete transformation JSON</summary><textarea id="provenance" readonly aria-label="Complete transformation provenance"></textarea></details>'
    page += '<p><a href="trace.json" download="refinement-trace.json">Download transformation JSON</a> · <a href="raw-samples.json" download="preserved-qcbm-samples.json">Download original samples</a> · <a href="harmonic-analysis.json" download="harmonic-analysis.json">Bar-by-bar harmony JSON</a> · <a href="analysis.json" download="comparison-analysis.json">Diagnostics JSON</a></p>'
    page += '<script type="application/json" id="trace-data">'+provenance+'</script>'
    page += '''<script>
const players=[...document.querySelectorAll('audio')];
players.forEach(player=>player.addEventListener('play',()=>players.forEach(other=>{if(other!==player)other.pause()})));
document.getElementById('texture').addEventListener('change',event=>{
 players.forEach(player=>player.pause());
 document.querySelectorAll('[data-texture]').forEach(panel=>panel.hidden=panel.dataset.texture!==event.target.value);
});
document.getElementById('provenance').value=JSON.stringify(JSON.parse(document.getElementById('trace-data').textContent),null,2);
</script></html>'''
    (out/'listen.html').write_text(page,encoding='utf-8')
