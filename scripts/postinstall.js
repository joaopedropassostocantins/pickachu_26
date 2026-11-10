#!/usr/bin/env node
import { trackInstall } from '../lib/telemetry.js';
import pkg from '../package.json' assert { type: 'json' };

trackInstall({ version: pkg.version }).catch(() => {});