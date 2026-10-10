// Private scratch diagnostic entry point; never used by the production duet UI.
import * as diagnostic from 'probe';
const raw = String(await diagnostic.probe_json.callPromising(backend, 32));
document.body.textContent = raw;
console.log(raw);
