import {mountDuet} from '/ui.mjs';
import {mountComposition} from '/composition-mode.mjs';
async function load(path) { const r=await fetch(path); const data=await r.json(); if(!r.ok)throw Error(data.error);return data; }
const experiment=mountDuet(() => {throw Error('Private package preview: live backend execution disabled');},
  'LOCAL PACKAGE PREVIEW · no live backend bridge · RECORDED fixture only', {loadFixture:()=>load('/api/fixture')});
mountComposition(()=>load('/api/composition'));
await experiment;
