"""Persistent offline SFZ voices through the public sfizz C API."""
import ctypes as ct
from ctypes.util import find_library
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from .performance import performance_for
from .composition.performer import validate_performance

# Keyswitch values are MIDI pitches (SFZ uses C4 = MIDI 60).
PATCHES = {
    "flute": ("Flute-KS.sfz", {"sustained":36, "connected":36, "accented":36, "detached":39}),
    "clarinet": ("Clarinet-KS.sfz", {"sustained":36, "connected":36, "accented":36, "detached":37}),
    "violin_1": ("ViolinEns-KS.sfz", {"sustained":36,"connected":36,"accented":36,"detached":38,"pizzicato":39}),
    "violin_2": ("ViolinEns-KS.sfz", {"sustained":36,"connected":36,"accented":36,"detached":38,"pizzicato":39}),
    "viola": ("ViolaEns-KS.sfz", {"sustained":36,"connected":36,"accented":36,"detached":38,"pizzicato":39}),
    "cello": ("CelloEns-KS.sfz", {"sustained":84,"connected":84,"accented":84,"detached":86,"pizzicato":87}),
    "double_bass": ("Contrabass-KS.sfz", {"sustained":84,"connected":84,"accented":84,"detached":87,"pizzicato":88}),
    "piano": ("VSUpright1.sfz", {}),
    "piccolo": ("PiccoloSus.sfz", {}), "oboe": ("OboeSusNV.sfz", {}),
    "bassoon": ("BassoonSus.sfz", {}), "horns": ("FHornSus.sfz", {}),
    "trumpets": ("TrumpetSus.sfz", {}), "trombones": ("TromboneSus.sfz", {}),
    "tuba": ("Tuba-KS.sfz", {"sustained":84,"connected":84,"accented":84,"detached":85}),
    "timpani": ("Timpani.sfz", {}), "percussion": ("GM-StylePerc.sfz", {}),
}
PLAYABLE_RANGES = {
    "flute":(60,96), "clarinet":(50,90), "violin_1":(55,86), "violin_2":(55,86),
    "viola":(48,86), "cello":(36,77), "double_bass":(24,60), "piano":(24,103),
    "piccolo":(67,91), "oboe":(58,89), "bassoon":(34,75), "horns":(33,77),
    "trumpets":(52,84), "trombones":(34,65), "tuba":(29,62), "timpani":(36,60),
    "percussion":(32,104),
}


def discover_acoustic(config):
    root = Path(__file__).resolve().parents[1]
    receipt = None
    roots = [root / "assets" / "acoustic"]
    if os.environ.get("QML_ACOUSTIC_ASSETS"):
        roots.insert(0, Path(os.environ["QML_ACOUSTIC_ASSETS"]))
    for candidate in roots:
        if (candidate / "receipt.json").is_file():
            receipt = json.loads((candidate / "receipt.json").read_text(encoding="utf-8"))
            break
    library = config.sfizz_library or os.environ.get("SFIZZ_LIBRARY") or (receipt or {}).get("library") or find_library("sfizz")
    samples = config.sample_library or os.environ.get("VSCO_PATH") or (receipt or {}).get("samples")
    if not library or not samples or not Path(samples).is_dir():
        raise OSError("Acoustic assets unavailable. Run scripts/setup_acoustic.py or supply --sfizz-library and --sample-library; no fallback was used.")
    return str(library), Path(samples).resolve(), receipt


def _sample_path(path):
    text = str(path.resolve())
    if os.name == "nt" and not text.isascii():
        # sfizz's Windows 1.2.3 file reader needs an ANSI-compatible sample path.
        buffer = ct.create_unicode_buffer(32768)
        fn = ct.windll.kernel32.GetShortPathNameW
        fn.argtypes = [ct.c_wchar_p,ct.c_wchar_p,ct.c_uint]
        fn.restype = ct.c_uint
        count = fn(text,buffer,len(buffer))
        if not count or count >= len(buffer) or not buffer.value.isascii():
            raise OSError("sfizz needs ASCII sample paths on Windows. Install assets in an ASCII directory and supply --sample-library.")
        text = buffer.value
    return text.encode("utf-8")


class SfzSynth:
    def __init__(self, library, patch, rate, block_size=256):
        self.synth = None
        self.directory = None
        if os.name == "nt":
            self.directory = os.add_dll_directory(str(Path(library).resolve().parent))
        try:
            self.lib = ct.CDLL(library)
            p, i, f = ct.c_void_p, ct.c_int, ct.c_float
            signatures = {
                "sfizz_create_synth":(p,[]), "sfizz_free":(None,[p]),
                "sfizz_set_sample_rate":(None,[p,f]), "sfizz_set_samples_per_block":(None,[p,i]),
                "sfizz_set_num_voices":(None,[p,i]), "sfizz_load_file":(ct.c_bool,[p,ct.c_char_p]),
                "sfizz_set_preload_size":(None,[p,ct.c_uint]),
                "sfizz_send_note_on":(None,[p,i,i,i]), "sfizz_send_note_off":(None,[p,i,i,i]),
                "sfizz_send_cc":(None,[p,i,i,i]),
                "sfizz_render_block":(None,[p,ct.POINTER(ct.POINTER(f)),i,i]),
            }
            for name,(result,args) in signatures.items():
                fn = getattr(self.lib,name)
                fn.restype, fn.argtypes = result,args
            self.synth = self.lib.sfizz_create_synth()
            if not self.synth:
                raise RuntimeError("sfizz allocation failed")
            self.lib.sfizz_set_sample_rate(self.synth,rate)
            self.lib.sfizz_set_samples_per_block(self.synth,block_size)
            self.lib.sfizz_set_num_voices(self.synth,256)
            self.lib.sfizz_set_preload_size(self.synth,8*1024*1024)
            if not self.lib.sfizz_load_file(self.synth,_sample_path(patch)):
                raise RuntimeError("sfizz could not load " + str(patch))
            # Preload the full samples for reproducible offline rendering: no streaming underruns.
            self.block_size = block_size
            self.buffer = np.zeros((2,block_size),dtype=np.float32)
            self.channels = (ct.POINTER(f)*2)(*[row.ctypes.data_as(ct.POINTER(f)) for row in self.buffer])
        except Exception:
            self.close()
            raise

    def event(self, kind, delay, key, value):
        fn = {"on":self.lib.sfizz_send_note_on,"off":self.lib.sfizz_send_note_off,"cc":self.lib.sfizz_send_cc}[kind]
        fn(self.synth,delay,key,value)

    def frames(self,count):
        self.lib.sfizz_render_block(self.synth,self.channels,2,count)
        return self.buffer[:,:count].T.copy()

    def close(self):
        if self.synth:
            self.lib.sfizz_free(self.synth)
            self.synth = None
        if self.directory:
            self.directory.close()
            self.directory = None


def room_reverb(dry,rate,wet):
    """One shared deterministic, damped algorithmic room; original dry stems retained."""
    if wet == 0:
        return dry.copy()
    length = round(rate*1.6)
    rng = np.random.default_rng(1001)
    impulse = rng.normal(size=(length,2)).astype(np.float32)
    # Low-pass diffusion and decay; no modulation of individual notes.
    kernel = np.ones(max(2,round(rate*.0004)),dtype=np.float32)
    kernel /= len(kernel)
    for channel in range(2):
        impulse[:,channel] = np.convolve(impulse[:,channel],kernel,mode="same")
    time = np.arange(length)/rate
    impulse *= (np.exp(-time*4.8)*(time>=.025))[:,None]
    impulse /= max(.001,float(np.sqrt(np.sum(impulse**2)/2)))
    for delay,level in [(.017,.35),(.031,.25),(.047,.18),(.071,.12)]:
        impulse[round(delay*rate)] += level
    size = 1 << (len(dry)+length-2).bit_length()
    reflected = np.fft.irfft(np.fft.rfft(dry,n=size,axis=0)*np.fft.rfft(impulse,n=size,axis=0),n=size,axis=0)[:len(dry)]
    return (dry + wet*reflected).astype(np.float32)


def render_acoustic(score, performance, config):
    validate_performance(score,performance)
    library,samples,receipt = discover_acoustic(config)
    rate = config.sample_rate
    seconds = performance.timeline.seconds_at(score.end_tick)
    total = round((seconds+4)*rate)
    stems, patches, limitations = {},{},list(performance.warnings)
    for part in score.parts:
        if part.instrument not in PATCHES:
            raise ValueError("No acoustic patch mapping for " + part.instrument)
        filename, switches = PATCHES[part.instrument]
        patch = samples / filename
        if not patch.is_file():
            raise OSError("Required acoustic patch missing: " + str(patch))
        notes = [n for n in performance.notes if n.part_id == part.id]
        low,high = PLAYABLE_RANGES[part.instrument]
        if any(not low<=n.pitch<=high for n in notes):
            raise ValueError(part.id + ": a note exceeds the VSCO patch range; select a compatible octave in the logical score")
        events = []
        def at(tick):
            return round(performance.timeline.seconds_at(tick)*rate)
        for note in notes:
            start, end = at(note.onset_tick),at(note.onset_tick+note.duration_ticks)
            if switches:
                switch = switches[note.articulation]
                # Engine-only control notes never enter logical/performed MIDI or lineage.
                events.append((start,1,"on",switch,1))
                events.append((start,2,"off",switch,0))
            elif note.articulation not in ("sustained","connected","accented"):
                limitations.append(part.instrument + ": articulation uses note gating; no dedicated sample in this mapping")
            events.extend([(start,3,"on",note.pitch,note.velocity),(end,0,"off",note.pitch,0)])
        # Expression is applied smoothly to the complete part, without replacing sample envelopes.
        cc = performance.controls[part.id]
        events.extend((at(c.tick),0,"cc",64,c.value) for c in cc if c.controller==64)
        events.sort()
        synth = SfzSynth(library,patch,rate)
        try:
            data = np.zeros((total,2),dtype=np.float32)
            cursor = 0
            for start in range(0,total,synth.block_size):
                count = min(synth.block_size,total-start)
                while cursor<len(events) and events[cursor][0]<start+count:
                    frame,_,kind,key,value = events[cursor]
                    synth.event(kind,max(0,frame-start),key,value)
                    cursor += 1
                data[start:start+count] = synth.frames(count)
        finally:
            synth.close()
        if notes and float(np.max(np.abs(data))) < 1e-7:
            raise RuntimeError("Acoustic part rendered silently: " + part.id)
        expression = [c for c in cc if c.controller==11]
        if expression:
            positions = [at(c.tick) for c in expression]
            levels = [c.value/100 for c in expression]
            data *= np.interp(np.arange(total),positions,levels).astype(np.float32)[:,None]
        volume = score.performance.get(part.id,performance_for(part.instrument)).volume
        # Balance preserves each stereo recording; modest channel attenuation gives seating.
        pan = (part.pan-64)/64
        stereo = np.array([1-max(0,pan)*.55,1-max(0,-pan)*.55],dtype=np.float32)
        stems[part.id] = data * volume * stereo
        patches[part.id] = {"patch":filename,"sha256":hashlib.sha256(patch.read_bytes()).hexdigest(),
                            "kind":"section" if "Ens" in filename else "solo",
                            "keyswitches":switches}
    dry = np.sum(list(stems.values()),axis=0)
    mix = room_reverb(dry,rate,config.reverb_wet)
    return mix,stems,{"renderer":"sfizz 1.2.3 persistent SFZ voices","sample_library":"VSCO 2 CE 1.1.0",
        "sample_rate":rate,"patches":patches,"asset_receipt":receipt,
        "room":"shared algorithmic room; wet="+str(config.reverb_wet),
        "limitations":sorted(set(limitations)),"native_envelopes_preserved":True}
