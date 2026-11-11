/** Mantido para compatibilidade manual; não é executado por npm install. */
import { trackInstall } from '../lib/telemetry.js';
const result = await trackInstall({ version: '2.1.0' });
if (result) console.info('[pikachu] Metadados locais:', result);
