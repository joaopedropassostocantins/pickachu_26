#!/usr/bin/env node
import fs from 'node:fs';
import { trackInstall } from '../lib/telemetry.js';
try {
  const pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
  trackInstall({ version: pkg.version });
} catch {
  // Sem impacto na instalação.
}
