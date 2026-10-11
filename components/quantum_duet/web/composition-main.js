// Optional Qollab entry; the original Experiment UI/executor are unchanged.
import * as recorded from 'quantum_duet.recorded_fixture';
import * as inference from 'quantum_duet.integration';
import * as composition from 'quantum_duet.composition_showcase';
import { mountDuet, parsePythonJSON } from './ui.mjs';
import { mountComposition } from './composition-mode.mjs';
const experiment = mountDuet(async ({shots, mode, executionType}) => {
  const proxy = await inference.generate_take.callPromising(backend, shots, mode, executionType);
  return parsePythonJSON(proxy);
}, 'Qollab RAW duet · creative orchestration runs locally. Select a FREE simulator in Select QPU. Simulator type below is your declaration.', {
  loadFixture: async () => String(await recorded.load_fixture.callPromising()),
});
mountComposition(async () => parsePythonJSON(await composition.load_showcase.callPromising()));
await experiment;
