// Registro local e facultativo de instalação: nenhuma chamada à rede.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export function trackInstall({ version } = {}) {
  if (process.env.PIKACHU_ANALYZER_TELEMETRY !== '1') return;
  try {
    const dir = path.join(os.homedir(), '.local', 'share', 'pikachu-analyzer');
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
    const file = path.join(dir, 'telemetry.json');
    const previous = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : { installs: 0 };
    const record = {
      installs: (Number(previous.installs) || 0) + 1,
      last_version: String(version || 'unknown'),
      updated_at: new Date().toISOString()
    };
    fs.writeFileSync(file, JSON.stringify(record, null, 2), { mode: 0o600 });
  } catch {
    // Telemetria local opcional nunca quebra a instalação.
  }
}
