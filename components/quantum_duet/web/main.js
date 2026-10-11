// Qollab entry: only the documented asynchronous Python bridge; no local fallback.
import * as recorded from 'quantum_duet.recorded_fixture';
import * as inference from 'quantum_duet.joint_cue';
import { mountDuet, parsePythonJSON } from './ui.mjs';
await mountDuet(async ({shots, mode, executionType}) => {
  const proxy = await inference.run_selected.callPromising(backend, shots, mode, executionType);
  return parsePythonJSON(proxy);
}, 'Qollab RAW duet · creative orchestration runs locally. Select a FREE simulator in Select QPU. Simulator type below is your declaration.', {
 loadFixture: async () => String(await recorded.load_fixture.callPromising()),
 // Full orchestration stays an explicitly separate local CPython creative feature.
});
