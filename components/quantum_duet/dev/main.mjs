import {mountDuet} from '/web/ui.mjs';
const configResponse=await fetch('/api/config');
if(!configResponse.ok)throw Error('Local arrangement configuration unavailable');
const config=await configResponse.json();
await mountDuet(async ({shots,mode})=>{
 const response=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({shots,mode})});
 const data=await response.json();if(!response.ok)throw Error(data.error);return data;
},'LOCAL DEVELOPMENT · CPython BasicSimulator · fixed regression seeds · NOT Qollab bridge', {
 arrangementBackend: config.arrangement_backend,
 arrange: async (raw_envelope_text,raw_source_text) => {
  const response=await fetch('/api/arrange',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({raw_envelope_text,raw_source_text})});
  const data=await response.json();if(!response.ok)throw Error(data.error);return data;
 },
 loadFixture: async () => {
  const response=await fetch('/api/fixture');
  if(!response.ok)throw Error(`Recorded fixture HTTP ${response.status}`);
  return response.text();
 }
});
