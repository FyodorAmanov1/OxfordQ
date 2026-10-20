// Independent contract: actual joint-cue shots; never an equal-allocation envelope.
export const JOINT_CONTRACT='qm.joint-cue-result.v1';
const check=(yes,message)=>{if(!yes)throw Error(`Joint-cue result: ${message}`);};
const close=(a,b)=>typeof a==='number'&&Number.isFinite(a)&&Math.abs(a-b)<1e-12;
const canonical=v=>v===null||typeof v!=='object'?JSON.stringify(v):Array.isArray(v)?`[${v.map(canonical).join(',')}]`:`{${Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')}}`;
async function digest(v){const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(v)));return Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');}
export async function validateJoint(t) {
  check(t.contract_version===JOINT_CONTRACT&&t.status==='completed','unsupported contract/status');
  const e=t.execution,s=t.statistics,h=t.joint_histogram_yxba;
  check(e.backend_run_calls===1&&e.circuit_count===1&&e.simulator_verified===true&&e.hardware_executed===false&&e.bit_order==='yxba','execution allocation/identity');
  check(typeof e.job_id==='string'&&e.job_id.length>0&&t.run_id===`qm-joint-${e.job_id}`,'job/run identity');
  check(t.circuit.version==='qm.joint-cue-circuit.v1'&&t.circuit.bit_order==='yxba'&&t.circuit.angle_order.join(',')==='A0,A1,B0,B1','circuit metadata');
  check(!t.fallback.used&&t.errors.length===0&&t.base_melody.generated_now===false&&t.base_melody.data_status==='RECORDED','source/fallback labels');
  const ns=[0,0,0,0],ws=[0,0,0,0],cs=[0,0,0,0],unused={...h};
  for(const [bits,n] of Object.entries(h)){
    check(/^[01]{4}$/.test(bits)&&Number.isInteger(n)&&n>=0,'integer yxba counts');
    const [y,x,b,a]=Array.from(bits,Number),i=2*x+y;ns[i]+=n;ws[i]+=((a^b)===x*y?n:0);cs[i]+=a===b?n:-n;
  }
  const total=ns.reduce((a,b)=>a+b,0);
  check(total>=16&&total===e.returned_shots&&total===e.requested_shots&&total===s.total_independent_shots,'actual shot accounting');
  check(await digest(h)===t.histogram_sha256,'histogram hash');
  check(s.allocation.length===4,'four observed allocations');
  for(let i=0;i<4;i++){
    const r=s.allocation[i];check(r.x===Math.floor(i/2)&&r.y===i%2&&r.shots===ns[i]&&r.wins===ws[i],'allocation/wins');
    check(ns[i]?close(r.correlation,cs[i]/ns[i])&&close(r.success,ws[i]/ns[i]):r.correlation===null&&r.success===null,'conditional correlation');
    const expected={};for(const [bits,n] of Object.entries(h))if(Number(bits[1])===r.x&&Number(bits[0])===r.y)expected[bits.slice(2)]=n;
    check(canonical(r.counts_ba)===canonical(expected),'conditional histogram');
  }
  check(close(s.pooled_success,ws.reduce((a,b)=>a+b,0)/total)&&s.postselection===false&&s.hardware_certified===false,'pooled statistic/limitations');
  if(ns.every(n=>n>0)){
    const p=ws.reduce((a,w,i)=>a+w/ns[i],0)/4,r=Math.sqrt(Math.log(40)/2*ns.reduce((a,n)=>a+1/(16*n),0));
    check(s.conditional_available&&close(s.expected_success,p)&&close(s.chsh,8*p-4)&&close(s.hoeffding_radius,r),'weighted estimator');
    check(close(s.success_interval[0],Math.max(0,p-r))&&close(s.success_interval[1],Math.min(1,p+r)),'conditional interval');
  }else check(!s.conditional_available&&s.expected_success===null&&s.chsh===null&&s.success_interval===null,'empty setting must remain unavailable');
  const commitments={indices:[],strategies:[]};
  check(t.randomness.cue_redraws===0&&t.randomness.committed_before_backend_submission&&t.randomness.independent_streams,'independent precommitment/no cue redraw');
  for(let i=0;i<16;i++){
    const q=t.rounds.quantum[i],c=t.rounds.classical[i],id=`${t.run_id}/r${String(i).padStart(2,'0')}`;
    const bits=q.source_measurement.displayed_yxba;check(unused[bits]>0,'excerpt must be drawn without replacement');unused[bits]--;
    const [y,x,b,a]=Array.from(bits,Number);
    check(q.x===x&&q.y===y&&q.a===a&&q.b===b&&q.displayed_ba===bits.slice(2)&&q.win===((a^b)===x*y),'cue/output association');
    check(t.cue_sequence[i].join(',')===`${x},${y}`,'no independent playback cues');
    check(c.shared_strategy.length===4&&c.shared_strategy.every(v=>v===0||v===1)&&Number.isInteger(c.shared_strategy_index)&&c.shared_strategy_index>=0&&c.shared_strategy_index<8,'classical precommitment');
    commitments.indices.push(c.shared_strategy_index);commitments.strategies.push(c.shared_strategy);
    check(c.a===c.shared_strategy[x]&&c.b===c.shared_strategy[2+y]&&c.win===((c.a^c.b)===x*y),'local classical policy');
    for(const r of [q,c])check(r.run_id===t.run_id&&r.round_id===id&&r.round===i&&r.x===x&&r.y===y&&r.required_parity===x*y&&r.base_token===t.base_melody.tokens[i]&&r.source_measurement.histogram_sha256===t.histogram_sha256&&r.source_measurement.reconstructed_index===i&&r.source_measurement.displayed_yxba===bits,'paired round/source identity');
  }
  check(await digest(commitments)===t.randomness.classical_commitment_sha256&&e.classical_commitment_sha256===t.randomness.classical_commitment_sha256,'classical commitment hash');
  for(const method of ['quantum','classical']){
    check(t.rounds[method].length===16&&t.events[method].length===32,'retain every rest/round');
    check(t.excerpt[method].rounds===16&&t.excerpt[method].wins===t.rounds[method].filter(r=>r.win).length,'excerpt score');
    const ids=new Set();
    for(const event of t.events[method]){
      const r=t.rounds[method][event.round],output=event.voice==='alice'?r?.a:r?.b;
      check(r&&['alice','bob'].includes(event.voice)&&event.event_id===`${r.round_id}/${method}/${event.voice}`&&!ids.has(event.event_id),'event identity');ids.add(event.event_id);
      const token=r.base_token,index=token-1+output,pitch=token===0?null:(event.voice==='alice'?72:48)+12*Math.floor(index/7)+[0,2,4,5,7,9,11][index%7];
      check(Number.isInteger(token)&&token>=0&&token<=7&&event.run_id===t.run_id&&event.round_id===r.round_id&&event.base_token===token&&event.local_output===output&&event.rest===(token===0)&&event.pitch_midi===pitch&&event.velocity===80&&event.onset_beats===r.round+output*.5&&event.duration_beats===.4&&canonical(event.source_measurement)===canonical(r.source_measurement),'unchanged direct musical mapping');
    }
  }
  return t;
}
