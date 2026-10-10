import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertTake,DuetAudio,midiBytes,parsePythonJSON} from '../web/ui.mjs';

const take=JSON.parse(fs.readFileSync(new URL('./fixtures/qollab-local-run.json',import.meta.url)));
assertTake(take);
const frozen=JSON.stringify(take),shots=take.statistics.total_independent_shots;
assert.deepEqual(parsePythonJSON(frozen),take);
assert.deepEqual(parsePythonJSON({toJs:()=>frozen}),take);
assert.throws(()=>parsePythonJSON({toJs:()=>new Map()}),/Expected validated Python JSON text/);
let nextFrame=0;
global.requestAnimationFrame=()=>++nextFrame;
global.cancelAnimationFrame=()=>{};
class Context {
  constructor(){this.currentTime=0;this.oscillators=[];this.pending=[];this.destination={};}
  resume(){return new Promise(resolve=>this.pending.push(resolve));}
  createGain(){return {gain:{value:0,setValueAtTime(value){this.value=value;},linearRampToValueAtTime(value){this.value=value;}},connect(){},disconnect(){}};}
  createPeriodicWave(real,imag,options){return {real,imag,options};}
  createOscillator(){
    const osc={active:false,frequency:{value:0},setPeriodicWave(wave){this.wave=wave;},connect(){},
      start(){this.active=true;},stop(at){if(at===undefined)this.active=false;},disconnect(){this.active=false;}};
    this.oscillators.push(osc);return osc;
  }
}
const ctx=new Context(),states=[];
const audio=new DuetAudio(()=>{},(state,n)=>states.push([state,n]),()=>ctx);
const first=audio.play(take.events.quantum,120,{alice:false,bob:false});
const second=audio.play(take.events.quantum,120,{alice:false,bob:false});
ctx.pending.splice(0).forEach(resolve=>resolve());
await Promise.all([first,second]);
const count=take.events.quantum.filter(e=>!e.rest).length;
assert.equal(audio.nodes.length,count);
assert.equal(ctx.oscillators.filter(o=>o.active).length,count);
audio.mute('alice',true);
assert.equal(audio.voices.alice.gain.value,0);
audio.stop();
assert.equal(audio.nodes.length,0);
assert.equal(ctx.oscillators.filter(o=>o.active).length,0);
const third=audio.play(take.events.classical,90,{alice:false,bob:true});
audio.stop();ctx.pending.splice(0).forEach(resolve=>resolve());await third;
assert.equal(audio.nodes.length,0); // stopping while resume is pending cannot restart audio
assert.equal(JSON.stringify(take),frozen);
assert.equal(take.statistics.total_independent_shots,shots);
for(const method of ['quantum','classical']){
  const midi=midiBytes(take.events[method],120);
  assert.equal(String.fromCharCode(...midi.slice(0,4)),'MThd');

}
console.log(JSON.stringify({status:'passed',timestamp_utc:new Date().toISOString(),
  checks:['play race cancels stale resume','repeat Play does not stack','mute/stop cleanup',
    'Stop during resume','playback preserves take and experimental shots','both MIDI headers'],
  scope:'Node 16 fake AudioContext; real browser checks are recorded separately',states},null,2));
