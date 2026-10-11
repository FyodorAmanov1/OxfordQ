"""SoundFont preview rendering and matched comparison loudness."""
from __future__ import annotations

import os
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from .models import OrchestrationConfig


def discover_audio(config: OrchestrationConfig) -> tuple[str | None, Path | None]:
    root = Path(__file__).resolve().parent.parent
    executable = config.fluidsynth or os.environ.get("FLUIDSYNTH_PATH") or shutil.which("fluidsynth")
    if not executable:
        candidates = sorted((root / "assets").glob("fluidsynth/**/fluidsynth.exe"))
        if candidates:
            executable = str(candidates[0])
    soundfont = config.soundfont
    if soundfont is None and os.environ.get("SOUNDFONT_PATH"):
        soundfont = Path(os.environ["SOUNDFONT_PATH"])
    if soundfont is None:
        candidates = sorted((root / "assets").glob("soundfonts/**/*.sf2"))
        if candidates:
            soundfont = candidates[0]
    return executable, soundfont


def _pcm(path: Path) -> tuple[np.ndarray, tuple]:
    with wave.open(str(path), "rb") as audio:
        channels, width, rate = audio.getnchannels(), audio.getsampwidth(), audio.getframerate()
        if width != 2:
            raise ValueError("Expected 16-bit PCM from FluidSynth")
        data = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float64) / 32768
    return data.reshape(-1, channels), (channels, width, rate)


def _write_pcm(path: Path, data: np.ndarray, format_: tuple) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(format_[0])
        audio.setsampwidth(2)
        audio.setframerate(format_[2])
        pcm = np.rint(np.clip(data, -1, 32767/32768) * 32768).astype("<i2")
        audio.writeframes(pcm.tobytes())


def render_comparisons(midis: dict[str, Path], config: OrchestrationConfig, *, scores=None, performances=None) -> tuple[dict[str, str], dict]:
    if config.audio_renderer == "sfizz":
        return _render_acoustic_comparisons(midis, config, scores, performances)
    executable, font = discover_audio(config)
    if not executable or font is None or not font.is_file():
        return {}, {"status": "unavailable", "message": "Install FluidSynth and provide a .sf2 SoundFont. See scripts/setup_audio.py, --fluidsynth and --soundfont."}
    if config.fluidsynth and not Path(executable).is_file() and not shutil.which(executable):
        return {}, {"status": "unavailable", "message": "Configured FluidSynth executable does not exist"}
    artifacts = {}
    diagnostics = {"status": "rendered", "soundfont": str(font.resolve()), "sample_rate": config.sample_rate}
    rendered = {}
    try:
        for name, midi in midis.items():
            destination = midi.with_suffix(".wav")
            playback_midi = midi.with_name(midi.stem + ".performed.mid") if performances is not None else midi
            if not playback_midi.is_file():
                raise ValueError("Performed MIDI is missing: " + str(playback_midi))
            command = [executable, "-ni", "-q", "-T", "wav", "-O", "s16", "-r", str(config.sample_rate),
                       "-g", "0.25", "-o", "synth.polyphony=512",
                       "-F", str(destination), str(font.resolve()), str(playback_midi.resolve())]
            process = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
            if process.returncode:
                raise RuntimeError(f"FluidSynth failed for {name}: {(process.stderr or process.stdout)[-1200:]}")
            data, format_ = _pcm(destination)
            rendered[name] = (destination, data, format_)
        # RMS over audible samples is a comparison proxy, not perceptual LUFS.
        rms = {}
        for name, (_, data, _) in rendered.items():
            audible = np.max(np.abs(data), axis=1) > 0.0005
            rms[name] = float(np.sqrt(np.mean(data[audible] ** 2))) if audible.any() else 0.0
        target = 10 ** (-20 / 20)
        gains = {name: target / value if value > 0 else 1.0 for name, value in rms.items()}
        peak = max((float(np.max(np.abs(data))) * gains[name] for name, (_, data, _) in rendered.items()), default=0)
        headroom = min(1.0, (10 ** (-1/20)) / peak) if peak else 1.0
        for name, (path, data, format_) in rendered.items():
            _write_pcm(path, data * gains[name] * headroom, format_)
            artifacts[f"{name}_wav"] = str(path.resolve())
        diagnostics.update({"normalization": "Matched audible-sample RMS with a shared gain reduction for -1 dBFS headroom; not LUFS",
                            "input_rms": rms})
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, wave.Error) as exc:
        diagnostics = {"status": "failed", "message": str(exc)}
        for name, (path, _, _) in rendered.items():
            artifacts[f"{name}_wav_unmatched"] = str(path.resolve())
    return artifacts, diagnostics


def _render_acoustic_comparisons(midis, config, scores, performances):
    from .acoustic_audio import render_acoustic
    if scores is None or performances is None:
        return {}, {"status":"failed", "message":"SFZ rendering requires logical scores and performance plans"}
    rendered, artifacts, details = {}, {}, {}
    try:
        for name,midi in midis.items():
            data,stems,info = render_acoustic(scores[name],performances[name],config)
            rendered[name] = (midi.with_suffix(".wav"),data,stems)
            details[name] = info
        rms = {}
        for name,(_,data,_) in rendered.items():
            audible = np.max(np.abs(data),axis=1) > .0005
            rms[name] = float(np.sqrt(np.mean(data[audible]**2))) if audible.any() else 0
            if rms[name] == 0:
                raise RuntimeError("Silent acoustic comparison: " + name)
        gains = {name:.1/value for name,value in rms.items()}
        peak = max(float(np.max(np.abs(data)))*gains[name] for name,(_,data,_) in rendered.items())
        headroom = min(1,(10**(-1/20))/peak) if peak else 1
        for name,(path,data,stems) in rendered.items():
            gain = gains[name]*headroom
            _write_pcm(path,data*gain,(2,2,config.sample_rate))
            artifacts[name+"_wav"] = str(path.resolve())
            stem_dir = path.parent / (name+".stems")
            stem_dir.mkdir(exist_ok=True)
            for part_id,stem in stems.items():
                stem_path = stem_dir / (part_id+".wav")
                _write_pcm(stem_path,stem*gain,(2,2,config.sample_rate))
                artifacts[name+"_stem_"+part_id] = str(stem_path.resolve())
        return artifacts,{"status":"rendered","renderer":"sfizz","performance":details,
            "input_rms":rms,"mix_gains":{n:g*headroom for n,g in gains.items()},
            "normalization":"One constant gain per mix; matched audible RMS and shared -1 dBFS headroom, not LUFS. Dry stems use their mix gain."}
    except (OSError,ValueError,RuntimeError) as exc:
        return artifacts,{"status":"failed","message":str(exc),"fallback_used":False}
