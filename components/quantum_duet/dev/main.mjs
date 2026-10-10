import {mountDuet} from '/web/ui.mjs';
await mountDuet(async ({shots,mode})=>{
 const response=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({shots,mode})});
 const data=await response.json();if(!response.ok)throw Error(data.error);return data;
},'LOCAL DEVELOPMENT · CPython BasicSimulator · fixed regression seeds · NOT Qollab bridge');
