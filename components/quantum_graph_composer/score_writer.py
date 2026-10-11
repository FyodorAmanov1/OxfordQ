"""MIDI writer adapted from the preserved prior extension."""
from pathlib import Path
import json,struct
INSTRUMENTS={'lead':{'channel':0,'program':0},'ostinato':{'channel':1,'program':0},'bass':{'channel':2,'program':32},'pad':{'channel':3,'program':89},'answer':{'channel':4,'program':73},'kick':{'channel':9,'program':0},'snare':{'channel':9,'program':0},'hat':{'channel':9,'program':0},'shaker':{'channel':9,'program':0}}

def vlq(value):
    result=[int(value)&127];value=int(value)>>7
    while value:result.insert(0,(value&127)|128);value>>=7
    return bytes(result)

def midi_bytes(score):
    ppq=480;tracks=[];tempo=round(60000000/score['metadata']['bpm'])
    tracks.append(b'\x00\xff\x51\x03'+tempo.to_bytes(3,'big')+b'\x00\xff\x58\x04\x04\x02\x18\x08\x00\xff\x2f\x00')
    for inst,info in INSTRUMENTS.items():
        selected=[e for e in score['events'] if e['instrument']==inst]
        if not selected:continue
        channel=info['channel'];messages=[]
        for e in selected:
            at=round(e['time_beats']*ppq);end=round((e['time_beats']+e['duration_beats'])*ppq)
            messages.extend([(at,1,bytes([0x90+channel,e['pitch'],e['velocity']])),(end,0,bytes([0x80+channel,e['pitch'],0]))])
        messages.sort(key=lambda m:(m[0],m[1]));name=inst.encode();track=b'\x00\xff\x03'+vlq(len(name))+name
        if channel!=9:track+=b'\x00'+bytes([0xc0+channel,info['program']])
        previous=0
        for at,_,message in messages:track+=vlq(at-previous)+message;previous=at
        tracks.append(track+b'\x00\xff\x2f\x00')
    midi=b'MThd'+struct.pack('>IHHH',6,1,len(tracks),ppq)+b''.join(b'MTrk'+struct.pack('>I',len(track))+track for track in tracks)
    return midi

def write_score(score,prefix):
    prefix=Path(prefix);prefix.parent.mkdir(parents=True,exist_ok=True)
    prefix.with_suffix('.json').write_text(json.dumps(score,indent=2),encoding='utf-8')
    prefix.with_suffix('.mid').write_bytes(midi_bytes(score))
    return {'json':str(prefix.with_suffix('.json')),'midi':str(prefix.with_suffix('.mid')),'events':len(score['events'])}
