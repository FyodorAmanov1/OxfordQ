// Native Web Audio rendering; no SoundFont library, network fetch or API key.
const gain={lead:.23,ostinato:.065,bass:.18,pad:.052,answer:.085,kick:.12,snare:.045,hat:.018};
const pan={lead:-.16,ostinato:.38,bass:0,pad:-.1,answer:-.4,kick:0,snare:-.08,hat:.48};
function randomFor(seed,event){
  let x=(seed ^ Math.imul(event.bar+1,2246822519) ^ Math.imul(Math.round(event.beat_in_bar*1000)+1,3266489917) ^ event.pitch)>>>0;
  return ()=>{x=(Math.imul(x,1664525)+1013904223)>>>0;return x/4294967296;};
}
function wave(buffer){
  const frames=buffer.length,n=frames*4,ab=new ArrayBuffer(44+n),v=new DataView(ab);
  const text=(at,s)=>[...s].forEach((c,i)=>v.setUint8(at+i,c.charCodeAt(0)));
  text(0,'RIFF');v.setUint32(4,n+36,true);text(8,'WAVE');text(12,'fmt ');v.setUint32(16,16,true);
  v.setUint16(20,1,true);v.setUint16(22,2,true);v.setUint32(24,buffer.sampleRate,true);
  v.setUint32(28,buffer.sampleRate*4,true);v.setUint16(32,4,true);v.setUint16(34,16,true);
  text(36,'data');v.setUint32(40,n,true);
  const l=buffer.getChannelData(0),r=buffer.getChannelData(1);let peak=0;
  for(let i=0;i<frames;i++)for(let ch=0;ch<2;ch++){
    let value=(ch?r:l)[i];
    value=.94*Math.tanh(1.68*value)*Math.min(1,i/(.035*buffer.sampleRate),(frames-1-i)/(2.5*buffer.sampleRate));
    peak=Math.max(peak,Math.abs(value));v.setInt16(44+4*i+2*ch,Math.round(value*32767),true);
  }
  return {wav:ab,peak,seconds:frames/buffer.sampleRate};
}
export async function renderAudio(score,bank){
  const fs=22050,spb=60/score.metadata.bpm;
  const endpoint=Math.max(...score.events.map(e=>e.time_beats+e.duration_beats))*spb;
  const seconds=Math.max(endpoint,score.metadata.nominal_duration_seconds)+3.5;
  const context=new OfflineAudioContext(2,Math.ceil(seconds*fs),fs);
  const dry=context.createGain();dry.connect(context.destination);
  for(const [time,g] of [[.103,.11],[.179,.09],[.283,.07],[.419,.055],[.607,.035]]){
    const delay=context.createDelay(1),volume=context.createGain();delay.delayTime.value=time;volume.gain.value=g;
    dry.connect(delay);delay.connect(volume);volume.connect(context.destination);
  }
  const regions=bank.regions.map(region=>{
    const bytes=Uint8Array.from(atob(region.pcm_base64),c=>c.charCodeAt(0)),view=new DataView(bytes.buffer);
    const buffer=context.createBuffer(1,bytes.length/2,region.rate),pcm=buffer.getChannelData(0);
    for(let i=0;i<pcm.length;i++)pcm[i]=view.getInt16(i*2,true)/32768;
    return {...region,buffer};
  });
  for(const event of score.events){
    const random=randomFor(score.metadata.seed,event),kind=event.instrument;
    const at=Math.max(0,event.time_beats*spb+(['lead','ostinato','answer'].includes(kind)?(random()-.5)*.018:0));
    const duration=event.duration_beats*spb;
    const volume=context.createGain(),position=context.createStereoPanner();position.pan.value=pan[kind]+(kind==='pad'?((event.pitch%5)-2)*.13:0);
    volume.connect(position);position.connect(dry);
    const amplitude=gain[kind]*(event.velocity/100)**1.25*(1+(random()-.5)*.05);
    const source=context.createBufferSource();source.connect(volume);
    if(kind==='lead'||kind==='ostinato'){
      const r=regions.find(r=>event.pitch>=r.low&&event.pitch<=r.high);
      const release=Math.min(1.2,r.release_seconds);source.buffer=r.buffer;source.loop=true;
      source.loopStart=r.loop_start/r.rate;source.loopEnd=r.loop_end/r.rate;
      source.playbackRate.value=2**((event.pitch-r.root+r.correction/100)/12);
      const level=amplitude*4*10**(-r.attenuation_cb/200),decay=Math.log(1e5)/r.decay_seconds;
      volume.gain.setValueAtTime(0,at);volume.gain.linearRampToValueAtTime(level,at+.004);
      volume.gain.exponentialRampToValueAtTime(Math.max(1e-6,level*Math.exp(-decay*duration)),at+duration);
      volume.gain.linearRampToValueAtTime(0,at+duration+release);
      source.start(at);source.stop(at+duration+release);
    }else{
      const release=kind==='pad'?.8:.25,length=Math.ceil((duration+release)*fs);
      const buffer=context.createBuffer(1,length,fs),pcm=buffer.getChannelData(0),f=440*2**((event.pitch-69)/12);
      let previous=0;
      for(let i=0;i<length;i++){
        const t=i/fs;let value=0;
        if(kind==='kick')value=Math.sin(2*Math.PI*(47*t+35*.024*(1-Math.exp(-t/.024))))*Math.exp(-18*t)*Math.min(1,t/.002);
        else if(kind==='snare'||kind==='hat'){
          const noise=(random()*2-1)*1.732;
          value=(kind==='snare'?.7*noise+.3*Math.sin(2*Math.PI*175*t):noise-.7*previous)*Math.exp(-(kind==='hat'?80:34)*t)*Math.min(1,t/.002);previous=noise;
        }else{
          const envelope=Math.min(1,t/(kind==='pad'?.32:.045))*Math.min(1,Math.max(0,(duration+release-t)/release));
          if(kind==='pad')for(let h=1;h<=6&&h*f<fs*.43;h++)value+=(Math.sin(2*Math.PI*f*h*1.0009*t+.3*h)+Math.sin(2*Math.PI*f*h*.9991*t-.2*h))/(2*h**1.8);
          else if(kind==='bass')value=(Math.sin(2*Math.PI*f*t)+.2*Math.sin(4*Math.PI*f*t)+.07*Math.sin(6*Math.PI*f*t))*(.7+.3*Math.exp(-3*t));
          else value=Math.sin(2*Math.PI*f*t+.012*Math.min(t/.4,1)*Math.sin(2*Math.PI*4.7*t))+.12*Math.sin(4*Math.PI*f*t);
          value*=envelope;
        }
        pcm[i]=value;
      }
      source.buffer=buffer;volume.gain.value=amplitude;source.start(at);
    }
  }
  return wave(await context.startRendering());
}
