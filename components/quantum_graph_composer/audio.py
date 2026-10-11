"""NumPy-only acoustic sample playback and a fixed chamber/electronic mix.

This is a small renderer for this piano bank, not a general SoundFont engine.
"""
from pathlib import Path
import base64
import json
import math
import wave
import numpy as np
from bridge import load_piano

PAN = {'lead':-.16,'ostinato':.38,'bass':0,'pad':-.1,'answer':-.4,
       'kick':0,'snare':-.08,'hat':.48}
GAIN = {'lead':.23,'ostinato':.065,'bass':.18,'pad':.052,'answer':.085,
        'kick':.12,'snare':.045,'hat':.018}


def piano(event, seconds, fs, bank):
    region = next(r for r in bank['regions'] if r['low'] <= event['pitch'] <= r['high'])
    samples = np.frombuffer(base64.b64decode(region['pcm_base64']), dtype='<i2').astype(float)/32768
    release = min(1.2, region['release_seconds'])
    t = np.arange(round((seconds+release)*fs))/fs
    rate = 2**((event['pitch']-region['root']+region['correction']/100)/12)
    positions = t*region['rate']*rate
    loop_start, loop_end = region['loop_start'], region['loop_end']
    positions = np.where(positions >= loop_end,
                         loop_start + (positions-loop_start) % (loop_end-loop_start), positions)
    signal = np.interp(positions, np.arange(len(samples)), samples)
    envelope = np.minimum(1,t/.004) * np.exp(-np.log(1e5)*t/region['decay_seconds'])
    envelope *= np.where(t>seconds,np.maximum(0,1-(t-seconds)/release)**2,1)
    return (signal*envelope*4*10**(-region['attenuation_cb']/200)).astype(np.float32)


def voice(event, seconds, fs, seed):
    kind = event['instrument']; release = .8 if kind=='pad' else .25
    t = np.arange(round((seconds+release)*fs))/fs
    frequency = 440*2**((event['pitch']-69)/12)
    if kind in ('kick','snare','hat'):
        random = np.random.default_rng(np.random.SeedSequence(
            [seed,event['bar'],round(event['beat_in_bar']*1000),event['pitch']]))
        noise = random.normal(0,1,len(t))
        if kind=='kick':
            signal=np.sin(2*np.pi*(47*t+35*.024*(1-np.exp(-t/.024))))*np.exp(-18*t)
        elif kind=='snare':
            signal=(.7*noise+.3*np.sin(2*np.pi*175*t))*np.exp(-34*t)
        else:
            signal=(noise-.7*np.r_[0,noise[:-1]])*np.exp(-80*t)
        return (signal*np.minimum(1,t/.002)).astype(np.float32)
    attack = .32 if kind=='pad' else .045
    envelope = np.minimum(1,t/attack)*np.minimum(1,np.maximum(0,(seconds+release-t)/release))
    if kind=='pad':
        signal=sum((np.sin(2*np.pi*frequency*h*1.0009*t+.3*h)+
                    np.sin(2*np.pi*frequency*h*.9991*t-.2*h))/(2*h**1.8)
                   for h in range(1,7) if h*frequency<fs*.43)
    elif kind=='bass':
        signal=np.sin(2*np.pi*frequency*t)+.2*np.sin(4*np.pi*frequency*t)+.07*np.sin(6*np.pi*frequency*t)
        envelope*=.7+.3*np.exp(-3*t)
    else:
        signal=np.sin(2*np.pi*frequency*t+.012*np.minimum(t/.4,1)*np.sin(2*np.pi*4.7*t))+.12*np.sin(4*np.pi*frequency*t)
    return (signal*envelope).astype(np.float32)


def render(score, path, sample_rate=22050):
    bank=json.loads(load_piano());fs=int(sample_rate);spb=60/score['metadata']['bpm']
    endpoint=max(e['time_beats']+e['duration_beats'] for e in score['events'])*spb
    duration=max(endpoint,score['metadata']['nominal_duration_seconds'])+3.5
    audio=np.zeros((math.ceil(duration*fs),2),dtype=np.float32)
    for event in score['events']:
        seconds=event['duration_beats']*spb
        signal=(piano(event,seconds,fs,bank) if event['instrument'] in ('lead','ostinato')
                else voice(event,seconds,fs,score['metadata']['seed']))
        random=np.random.default_rng(np.random.SeedSequence([score['metadata']['seed'],event['bar'],
                     round(event['beat_in_bar']*1000),event['pitch'],991]))
        jitter=float(random.uniform(-.009,.009)) if event['instrument'] in ('lead','answer','ostinato') else 0
        start=max(0,round((event['time_beats']*spb+jitter)*fs));stop=min(len(audio),start+len(signal))
        amplitude=GAIN[event['instrument']]*(event['velocity']/100)**1.25*(1+float(random.uniform(-.025,.025)))
        pan=PAN[event['instrument']]
        if event['instrument']=='pad':pan+=((event['pitch']%5)-2)*.13
        audio[start:stop,0]+=signal[:stop-start]*amplitude*math.cos((pan+1)*math.pi/4)
        audio[start:stop,1]+=signal[:stop-start]*amplitude*math.sin((pan+1)*math.pi/4)
    dry=audio.copy()
    for delay,gain in ((.103,.11),(.179,.09),(.283,.07),(.419,.055),(.607,.035)):
        offset=round(delay*fs)
        audio[offset:,0]+=gain*dry[:-offset,1];audio[offset:,1]+=gain*dry[:-offset,0]
    audio=.94*np.tanh(1.68*audio)
    fade=min(round(.035*fs),len(audio));tail=min(round(2.5*fs),len(audio))
    audio[:fade]*=np.linspace(0,1,fade)[:,None];audio[-tail:]*=np.linspace(1,0,tail)[:,None]
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as output:
        output.setnchannels(2);output.setsampwidth(2);output.setframerate(fs)
        output.writeframes(np.round(audio*32767).astype('<i2').tobytes())
    return {'path':str(path),'duration_seconds':len(audio)/fs,'sample_rate':fs,
            'peak':float(np.max(abs(audio))),'event_count':len(score['events']),
            'renderer':'Public-domain acoustic piano PCM; NumPy-only fixed stereo mix'}
