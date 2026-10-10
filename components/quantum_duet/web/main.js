// Qollab entry: only the documented asynchronous Python bridge; no local fallback.
import * as inference from 'quantum_duet.integration';
import { mountDuet, parsePythonJSON } from './ui.mjs';
await mountDuet(async ({shots, mode, executionType}) => {
  const proxy = await inference.generate_take.callPromising(backend, shots, mode, executionType);
  return parsePythonJSON(proxy);
}, 'Qollab supplied backend · select a FREE simulator in Select QPU. Simulator type below is your declaration.');
