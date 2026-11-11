/**
 * Telemetria local e não identificável.
 * Esta função NÃO envia dados pela rede nem coleta arquivos, tokens ou IDs.
 * Opt-out: PIKACHU_NO_TELEMETRY=1.
 */
import os from 'node:os';

export async function trackInstall({ version } = {}) {
  if (process.env.PIKACHU_NO_TELEMETRY === '1' || process.env.CI === 'true') {
    return null;
  }
  return {
    event: 'install',
    version: String(version || 'unknown'),
    node_major: process.versions.node.split('.')[0],
    platform: os.platform()
  };
}
