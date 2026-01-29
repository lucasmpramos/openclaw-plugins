#!/usr/bin/env node
// Apply a JSON "patch" to ~/.clawdbot/clawdbot.json with a conservative deep-merge.
// - Creates a timestamped backup next to the target config
// - Writes pretty JSON
// This is intentionally simple so it’s easy to audit.

import fs from 'node:fs';
import path from 'node:path';

function arg(flag) {
  const i = process.argv.indexOf(flag);
  return i === -1 ? null : (process.argv[i + 1] ?? null);
}

function deepMerge(dst, src) {
  if (src === null || src === undefined) return dst;
  if (Array.isArray(src)) return src; // patch arrays replace
  if (typeof src !== 'object') return src;
  if (typeof dst !== 'object' || dst === null || Array.isArray(dst)) dst = {};
  for (const [k, v] of Object.entries(src)) {
    dst[k] = deepMerge(dst[k], v);
  }
  return dst;
}

const patchPath = arg('--patch');
const configPath = arg('--config') || path.join(process.env.HOME || '/home/ubuntu', '.clawdbot', 'clawdbot.json');

if (!patchPath) {
  console.error('Usage: node apply-config-patch.mjs --patch <patch.json> [--config <clawdbot.json>]');
  process.exit(2);
}

const patch = JSON.parse(fs.readFileSync(patchPath, 'utf8'));
const original = JSON.parse(fs.readFileSync(configPath, 'utf8'));

const next = deepMerge(structuredClone(original), patch);

const ts = new Date().toISOString().replace(/[:.]/g, '-');
const backupPath = `${configPath}.bak.${ts}`;
fs.copyFileSync(configPath, backupPath);

fs.writeFileSync(configPath, JSON.stringify(next, null, 2) + '\n');

console.log(JSON.stringify({
  ok: true,
  configPath,
  backupPath,
  note: 'Restart the gateway to apply changes: clawdbot gateway restart'
}, null, 2));
