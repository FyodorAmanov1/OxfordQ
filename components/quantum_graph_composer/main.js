// Qollab supplies `backend`. callPromising is required for IonQ's async bridge.
import * as composer from 'bridge';
import { mountComposer } from './ui.mjs';
await mountComposer(
  async ({seed,bars,bpm,shots,interaction}) => String(await composer.generate.callPromising(backend,seed,bars,bpm,shots,interaction)),
  async () => String(await composer.load_piano.callPromising())
);
