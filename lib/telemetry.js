/**
 * Telemetry module for project-x.
 *
 * Follows the same pattern as popular Open Source packages
 * (e.g., Next.js, Astro, Nuxt) — opt-out via environment variable.
 *
 * Sent data (strictly):
 *   - Anonymous install ID (UUID v4, stored locally)
 *   - Package version (from package.json)
 *   - Node.js major version
 *   - OS platform (win32 | darwin | linux)
 *
 * Never sent:
 *   - File paths, repo names, environment variables, user identifiers
 *   - Any content from files being processed
 */

import crypto from 'node:crypto';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';

const TELEMETRY_ENDPOINT = 'https://telemetry.project-x.dev/v1/event';

function getOrCreateInstallId() {
  const dir = path.join(os.homedir(), '.project-x');
  const file = path.join(dir, 'install-id');

  try {
    fs.mkdirSync(dir, { recursive: true });
    if (fs.existsSync(file)) {
      return fs.readFileSync(file, 'utf-8').trim();
    }
    const id = crypto.randomUUID();
    fs.writeFileSync(file, id, { mode: 0o600 });
    return id;
  } catch {
    return null;
  }
}

export async function trackInstall({ version }) {
  // Opt-out conditions
  if (process.env.PROJECT_X_TELEMETRY === '0') return;
  if (process.env.CI === 'true') return;   // CI não telemetra
  if (process.env.NODE_ENV === 'test') return;
  if (!process.stdout.isTTY) return;       // Non-interactive shells não telemetram

  const installId = getOrCreateInstallId();
  if (!installId) return;

  const payload = {
    event: 'install',
    install_id: installId,
    version,
    node_major: process.versions.node.split('.')[0],
    platform: os.platform(),
    timestamp: new Date().toISOString(),
  };

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);

    await fetch(TELEMETRY_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': `project-x/${version}`,
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    }).finally(() => clearTimeout(timeout));
  } catch {
    // Telemetry nunca deve quebrar a instalação
  }
}