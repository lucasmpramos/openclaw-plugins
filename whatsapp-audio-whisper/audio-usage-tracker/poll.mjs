#!/usr/bin/env node
// Poll Clawdbot logs for new inbound WhatsApp audio messages and log them to Notion.
// Notion-Version: 2025-09-03

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const NOTION_VERSION = '2025-09-03';

function readKey() {
  const p = path.join(process.env.HOME || '/home/ubuntu', '.config/notion/api_key');
  return fs.readFileSync(p, 'utf8').trim();
}

async function notion(method, urlPath, body) {
  const key = readKey();
  const res = await fetch(`https://api.notion.com/v1${urlPath}`, {
    method,
    headers: {
      Authorization: `Bearer ${key}`,
      'Notion-Version': NOTION_VERSION,
      'Content-Type': 'application/json'
    },
    body: body ? JSON.stringify(body) : undefined
  });
  const text = await res.text();
  let json;
  try { json = text ? JSON.parse(text) : null; } catch { json = { raw: text }; }
  if (!res.ok) throw new Error(json?.message || json?.raw || `HTTP ${res.status}`);
  return json;
}

function parseArgs() {
  const args = process.argv.slice(2);
  const out = {};
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (!a.startsWith('--')) continue;
    out[a.slice(2)] = args[i + 1];
    i++;
  }
  return out;
}

function safeJsonParse(line) {
  try { return JSON.parse(line); } catch { return null; }
}

function getDurationSeconds(mediaPath) {
  // ffprobe is part of ffmpeg package
  try {
    const out = execFileSync('ffprobe', [
      '-v', 'error',
      '-show_entries', 'format=duration',
      '-of', 'default=noprint_wrappers=1:nokey=1',
      mediaPath
    ], { encoding: 'utf8' }).trim();
    const n = Number(out);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

const { log = '/tmp/clawdbot/clawdbot-2026-01-28.log', state, db } = parseArgs();
if (!state || !db) {
  console.error('Usage: node poll.mjs --db <database_id> --state <state.json> [--log <path>]');
  process.exit(1);
}

let st = { pos: 0, seen: {} };
if (fs.existsSync(state)) {
  try { st = JSON.parse(fs.readFileSync(state, 'utf8')); } catch {}
}

const stat = fs.statSync(log);
let start = st.pos || 0;
if (start > stat.size) start = 0;

const buf = fs.readFileSync(log);
const chunk = buf.subarray(start);
const text = chunk.toString('utf8');
const lines = text.split(/\n/).filter(Boolean);

let newCount = 0;

for (const line of lines) {
  // Fast filter to avoid JSON parse overhead.
  if (!line.includes('"mediaPath"') || !line.includes('"mediaType"') || !line.includes('audio/')) continue;

  const obj = safeJsonParse(line);
  if (!obj || !obj._meta?.date) continue;

  // We want the web-inbound records because they include mediaPath.
  // Example shape: {"0":"{\"module\":\"web-inbound\"}","1":{...},"2":"inbound message", ...}
  const mod = obj[0];
  const payload = obj[1];
  if (!String(mod || '').includes('web-inbound')) continue;
  if (!payload?.mediaPath || !payload?.mediaType) continue;
  if (!String(payload.mediaType).startsWith('audio/')) continue;

  const from = payload.from;
  const to = payload.to;
  const mediaPath = payload.mediaPath;
  const timestamp = obj._meta.date; // ISO

  const key = `${from}|${to}|${mediaPath}|${timestamp}`;
  if (st.seen?.[key]) continue;

  let sizeBytes = null;
  try { sizeBytes = fs.statSync(mediaPath).size; } catch {}
  const durationSec = getDurationSeconds(mediaPath);

  const name = `${new Date(timestamp).toISOString().slice(0,19)}Z ${from}`;

  // Create page
  await notion('POST', '/pages', {
    parent: { database_id: db },
    properties: {
      Name: { title: [{ type: 'text', text: { content: name } }] },
      Date: { date: { start: timestamp } },
      Channel: { select: { name: 'WhatsApp' } },
      From: { rich_text: [{ type: 'text', text: { content: String(from || '') } }] },
      MediaPath: { rich_text: [{ type: 'text', text: { content: String(mediaPath || '') } }] },
      DurationSec: { number: durationSec ?? null },
      SizeBytes: { number: sizeBytes ?? null },
      // We can’t reliably capture detected language / transcription latency from logs without more hooks.
      // Leave blank for now; we can enhance later.
      Language: { rich_text: [] },
      Model: { rich_text: [{ type: 'text', text: { content: 'whisper.cpp base (local)' } }] },
      TranscribeMs: { number: null },
      Success: { checkbox: true },
      Error: { rich_text: [] }
    }
  });

  st.seen = st.seen || {};
  st.seen[key] = 1;
  newCount++;
}

// advance file position
st.pos = stat.size;

// keep seen map bounded
const keys = Object.keys(st.seen || {});
if (keys.length > 5000) {
  const keep = keys.slice(-2000);
  const next = {};
  for (const k of keep) next[k] = 1;
  st.seen = next;
}

fs.mkdirSync(path.dirname(state), { recursive: true });
fs.writeFileSync(state, JSON.stringify(st, null, 2));

console.log(JSON.stringify({ changed: newCount > 0, newCount }, null, 2));
