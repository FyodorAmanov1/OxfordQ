"""Feedback composer; initial material and subsequent gestures come from graph.
The musical prior, ideal readout and classical mean-distance actuator are explicit.
"""
from pathlib import Path
import time,json
import numpy as np
from graph import MusicalGraph,probability,tilt_to_mean
from score_writer import write_score


SECTIONS=[('Introduction',4,.18),('Theme',8,.08),('Development',16,.27),
          ('Contrast',12,.46),('Recall',8,.06),('Further development',8,.32),('Coda',8,.04)]
def rng(seed,bar,role):return np.random.default_rng(np.random.SeedSequence([seed,bar,role]))
def plan():
    result=[];start=0
    for name,bars,target in SECTIONS:
        result.append({'name':name,'start_bar':start,'bars':bars,'variation_target':target});start+=bars
    return result
def select(p,u):return min(int(np.searchsorted(np.cumsum(p),u,side='right')),len(p)-1)
def degree_pitch(degrees,tonic,scale):
    d=np.asarray(degrees,int);return tonic+scale[d%7]+12*(d//7)
def harmony_distance(graph,reference):
    return np.array([1-len(set(c)&set(graph.chord_degrees[reference]))/3 for c in graph.chord_degrees])
def gesture_distance(graph,c,r,h,reference,scale):
    ints=np.diff(degree_pitch(graph.degrees,0,scale),axis=1)
    refints=np.diff(degree_pitch(graph.degrees[reference['contour']],0,scale))
    dc=np.mean(abs(ints-refints),axis=1)/8
    dr=np.mean(abs(graph.rhythms-graph.rhythms[reference['rhythm']]),axis=1)/3.5
    dh=harmony_distance(graph,reference['harmony'])
    return (.55*dc[:,None,None]+.25*dr[None,:,None]+.2*dh[None,None,:])
def musical_candidates(g,last_degree,last_harmony,tonic,scale,bar,section,theme_ref=None):
    # One start degree per contour and harmony; full gesture intervals preserved.
    options=np.arange(-7,15)
    possible=degree_pitch(g.degrees[:,None,:]+options[None,:,None],tonic+72,scale)
    inrange=(possible.min(axis=-1)>=62)&(possible.max(axis=-1)<=86)
    chordok=np.any(options[:,None,None]%7==g.chord_degrees[None,:,:],axis=-1)
    goal=last_degree if last_degree is not None else -1
    if theme_ref is not None and section['name'] in ['Theme','Recall']:
        goal=.55*theme_ref['start_degree']+.45*goal
    scores=abs(options[None,:]-goal)+.16*abs(options[None,:]+g.degrees.mean(axis=1)[:,None]-.5)
    costs=np.where(inrange[:,:,None]&chordok[None,:,:],scores[:,:,None],np.inf)
    selected=np.argmin(costs,axis=1);starts=options[selected]
    pitches=degree_pitch(g.degrees[:,None,:]+starts[:,:,None],tonic+72,scale)
    cost=np.zeros((64,g.shape[-2],8))
    # Reward common-tone harmonic changes, context continuity and chordal endings.
    if last_harmony is not None:cost+=1.4*harmony_distance(g,last_harmony)[None,None,:]
    end=g.degrees[:,-1,None]+starts
    chordal=np.array([[end[c,h]%7 in g.chord_degrees[h] for h in range(8)] for c in range(64)])
    cost+=.7*(~chordal)[:,None,:]
    span=np.ptp(pitches,axis=-1);cost+=.025*span[:,None,:]
    if bar%8==7:cost[:,:,0]-=1.2;cost[:,:,4]-=.7
    elif bar%8==6:cost[:,:,4]-=.6
    if section['name']=='Contrast':cost[:,:,3]-=.25;cost[:,:,5]-=.25
    if theme_ref is not None and section['name'] in ['Theme','Recall','Coda']:
        cost+=.12*np.mean(abs(pitches-np.array(theme_ref['lead_pitches'])[None,None,:]),axis=-1)[:,None,:]
    if bar==0 or bar>=62:
        cost[:,:,1:]+=30 # Explicit tonic opening/closing harmonic safeguard.
    # Texture is connected to rhythm rather than an independently random knob.
    return starts,pitches,cost
def pad_voicing(chord,last):
    from itertools import product
    pcs=set(int(p)%12 for p in chord);choices=[]
    for base in range(48,66):
        if base%12 not in pcs:continue
        notes=[base]
        while len(notes)<3:
            notes.append(min(p for p in range(notes[-1]+1,notes[-1]+13) if p%12 in pcs and p%12 not in {n%12 for n in notes}))
        choices.append(notes)
    return min(choices,key=lambda n:sum(abs(np.array(n)-last)))

def compose(seed=1201,bars=64,bpm=104,steps=64,interaction=.7,feedback_gain=.45,
            variation_control=True,readout_strength=1.,rhythm_count=16,
            contour_prior=None,engine=None,progress=None):
    begin=time.perf_counter();g=MusicalGraph(rhythm_count);nr=rhythm_count;r=rng(seed,0,999)
    tonic=int(r.choice([0,2,4,5,7,9]));minor=bool(r.random()<.55)
    scale=np.array([0,2,3,5,7,8,11] if minor else [0,2,4,5,7,9,11])
    initial=g.initial(seed);state=initial.copy()
    if contour_prior is not None:
        prior=np.asarray(contour_prior,float)
        if prior.shape!=(64,) or not np.isfinite(prior).all() or prior.min()<0 or prior.sum()<=0:
            raise ValueError('Invalid contour prior')
        state*=np.sqrt(64*prior/prior.sum()).reshape(4,4,4,1,1)
    if not 8<=bars<=64:raise ValueError('bars must be 8..64')
    if not 50<=bpm<=180:raise ValueError('bpm must be 50..180')
    if not 4<=steps<=128:raise ValueError('steps must be 4..128')
    sections=plan();theme=[];events=[];logs=[];harmonies=[];visited=np.zeros((64,8))
    last_degree=None;last_harmony=None;last_pad=np.array([55,60,64])+tonic
    maximum_norm_error=0;state_norm_error=0
    def add(bar,beat,dur,p,vel,part,tag):
        if dur>0:events.append({'time_beats':float(bar*4+beat),'duration_beats':float(dur),
            'pitch':int(p),'velocity':int(np.clip(round(vel),18,108)),'instrument':part,
            'bar':bar,'beat_in_bar':float(beat),'tag':tag})
    for bar in range(bars):
        section=next(s for s in sections if s['start_bar']<=bar<s['start_bar']+s['bars'])
        if bar>=max(8,bars-4) and bars<64:
            section={'name':'Coda','start_bar':bars-4,'bars':4,'variation_target':.04}
        local=bar-section['start_bar'];target=section['variation_target']
        reference=theme[(bar-4)%4] if len(theme)==4 and bar>=8 else None
        if 4<bar<8 and theme:
            reference=theme[0];target={5:.08,6:.035,7:.10}[bar]
        distances=gesture_distance(g,0,0,0,reference,scale) if reference else None
        feedback=np.broadcast_to((visited/(visited.max()+1))[:,None,:],(64,nr,8)).copy()
        if reference is not None:feedback+=.25*distances
        feedback*=feedback_gain
        duration=.45+.5*target
        state=(engine.step(g,state,duration,interaction,feedback,steps) if engine else
               g.step(state,duration,interaction,feedback,steps))
        state_norm_error=max(state_norm_error,abs(float(np.sum(abs(state)**2))-1))
        p=probability(state).reshape(64,nr,8)
        maximum_norm_error=max(maximum_norm_error,abs(float(p.sum())-1))
        starts,pitches,cost=musical_candidates(g,last_degree,last_harmony,tonic,scale,bar,section,reference)
        if reference is not None:
            # Distances use realizable semitone intervals, not nominal latent codes.
            di=np.mean(abs(np.diff(pitches,axis=-1)-np.diff(reference['lead_pitches'])[None,None,:]),axis=-1)/8
            dr=np.mean(abs(g.rhythms-np.array(reference['onsets'])[None,:]),axis=-1)/3.5
            dh=harmony_distance(g,reference['harmony'])
            distances=.55*di[:,None,:]+.25*dr[None,:,None]+.2*dh[None,None,:]
        weights=np.exp(-readout_strength*(cost-cost.min()))
        if bar==0 or bar>=bars-2:weights[:,:,1:]=0 # Exact classical tonic support constraint.
        conditioned=p*weights;conditioned/=conditioned.sum()
        constraint_tv=float(np.sum(abs(p-conditioned))/2)
        tilt=None;q=conditioned.ravel()
        if reference is not None and variation_control:
            q,tilt=tilt_to_mean(q,distances.ravel(),target)
        uniform=float(rng(seed,bar,10).random());index=select(q,uniform);c,rhythm,h=np.unravel_index(index,(64,nr,8))
        c,rhythm,h=int(c),int(rhythm),int(h)
        node={'contour':c,'rhythm':rhythm,'harmony':h}
        onset=g.rhythms[rhythm];lead=pitches[c,h].copy();degree=start=int(starts[c,h])
        if 4<=bar<8:theme.append({**node,'lead_pitches':lead.tolist(),'onsets':onset.tolist(),'start_degree':start})
        if bar==bars-1:lead=np.array([tonic+72]*4) # Logged ending override; one sustained note.
        energy=.48 if section['name']=='Introduction' else .8 if section['name']=='Contrast' else .66
        if section['name']=='Coda':energy=max(.25,.65-.05*local)
        chord=degree_pitch(g.chord_degrees[h],tonic+60,scale)
        pad=pad_voicing(chord,last_pad);last_pad=np.array(pad)
        for j,pitch in enumerate(pad):add(bar,.018*j,7 if bar==bars-1 else 3.92,pitch,35+12*energy,'pad','selected_harmony_voice_led')
        basspc=int(chord[0])%12
        bass=min([basspc+12*o for o in range(2,5) if 30<=basspc+12*o<=50],key=lambda x:abs(x-40))
        bassbeats=[0,2.5] if onset[1]<1 else [0,2]
        for j,b in enumerate(bassbeats):
            if bar==bars-1 and j:continue
            bp=bass if j==0 else min([int(chord[2])%12+12*o for o in range(3,5)],key=lambda x:abs(x-(bass+5)))
            add(bar,b,7 if bar==bars-1 else 1.65,bp,56+8*energy,'bass','graph_harmony_rhythm_support')
        leadactive=bar>=2
        durations=np.diff(np.append(onset,4))*.82
        if leadactive:
            for i,(beat,pitch,dur) in enumerate(zip(onset,lead,durations)):
                if bar==bars-1 and i:continue
                if section['name']=='Coda' and local>4 and i>1:continue
                add(bar,beat,6.8 if bar==bars-1 else dur,pitch,62+15*energy+(4 if i==0 else 0),
                    'lead','quantum_graph_material')
        # Accompaniment attacks arise from the chosen lead rhythm's complement.
        active=section['name']!='Introduction' or local>=2
        if active and not (section['name']=='Coda' and local>=5):
            for i,beat in enumerate(np.arange(0,4,.5)):
                if np.min(abs(onset-beat))<.1:continue
                pitch=int(pad[(i+h)%3])+(12 if pad[(i+h)%3]<60 else 0)
                add(bar,beat,.32,pitch,35+10*energy,'ostinato','complementary_onset_harmony')
        # Second conditional query chooses an independent answering contour/rhythm.
        answer_node=None
        if active and bar%2==1 and section['name'] not in ['Introduction','Coda']:
            answerlaw=q.reshape(64,nr,8)[:,:,h].copy()
            overlaps=np.mean(np.min(abs(g.rhythms[:,:,None]-onset[None,None,:]),axis=2)<.12,axis=1)
            contrast=np.mean(abs(g.degrees-g.degrees[c]),axis=1)/6
            answerlaw*=np.exp(-2*overlaps[None,:]+.7*contrast[:,None]);answerlaw/=answerlaw.sum()
            ai=select(answerlaw.ravel(),float(rng(seed,bar,11).random()));ac,ar=np.unravel_index(ai,(64,nr))
            answer_node={'contour':int(ac),'rhythm':int(ar),'conditioned_harmony':h}
            ap=pitches[ac,h]-12
            for i,beat in enumerate(g.rhythms[ar]):
                if np.min(abs(onset-beat))<.3:continue
                add(bar,beat,.65,ap[i],44+8*energy,'answer','conditional_graph_answer')
        if active and not(section['name']=='Coda' and local>=4):
            for b in [0,2]:add(bar,b,.2,36,40+8*energy,'kick','authored_meter')
            for b in [1,3]:add(bar,b,.12,38,25+5*energy,'snare','authored_meter')
            for b in onset[1:]:add(bar,float(b),.07,42,22+5*energy,'hat','selected_rhythm_accent')
        last_degree=int(start+g.degrees[c,-1]);last_harmony=h;visited[c,h]+=1
        realized_distance=float(distances[c,rhythm,h]) if distances is not None else None
        logs.append({'bar':bar,'section':section['name'],'node':node,'answer_node':answer_node,
            'lead_pitches':lead.tolist(),'onsets':onset.tolist(),'start_degree':start,
            'requested_variation':target if reference else None,'node_distance':realized_distance,
            'mean_distance_actuator':tilt,'constraint_TV':constraint_tv,
            'final_vs_raw_TV':float(np.sum(abs(q-p.ravel()))/2),
            'raw_entropy_bits':float(-np.sum(p*np.log2(np.maximum(p,1e-300)))),
            'readout_entropy_bits':float(-q@np.log2(np.maximum(q,1e-300))),
            'tonic_harmony_safeguard':bar==0 or bar>=bars-2,'lead_ending_override':bar==bars-1,
            'quantum_state_retained':True})
        harmonies.append({'bar':bar,'chord':g.chord_names[h],'chord_index':h,'chord_pitch_classes':sorted(int(p)%12 for p in chord)})
        if progress:progress(bar+1,bars)
    events.sort(key=lambda e:(e['time_beats'],e['instrument'],e['pitch']))
    realized_form=[]
    for decision in logs:
        if not realized_form or realized_form[-1]['name']!=decision['section']:
            realized_form.append({'name':decision['section'],'start_bar':decision['bar'],'bars':0})
        realized_form[-1]['bars']+=1
    score={'metadata':{'seed':seed,'model':'coherent-quantum-graph','bpm':bpm,'bars':bars,'nominal_duration_seconds':bars*4*60/bpm,
        'tonic_pc':tonic,'minor':minor,'key':['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'][tonic]+(' minor' if minor else ' major'),
        'generation_seconds':time.perf_counter()-begin,'graph_vertices':g.size,'qubits':int(np.log2(g.size)),'steps':steps,
        'interaction':interaction,'feedback_gain':feedback_gain,'variation_control':variation_control,
        'readout_strength':readout_strength,'ideal_readout':True,
        'maximum_probability_normalization_error':maximum_norm_error,
        'maximum_state_norm_error':state_norm_error,
        'engine':'Qiskit Statevector' if engine else 'structured NumPy unitary reference'},
        'events':events,'form':realized_form,'theme':theme,'harmony':harmonies,'decisions':logs,
        'graph':{'interval_values':[-2,-1,1,2],'rhythms':g.rhythms.tolist(),'chord_degree_sets':g.chord_degrees.tolist()}}
    return score
