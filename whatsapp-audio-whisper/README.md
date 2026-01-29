# WhatsApp Audio (Local) — whisper.cpp pack

This package documents and ships the **local WhatsApp audio pipeline** used in Luke’s Clawdbot instance.

What you get:
- Local audio transcription tool configuration (ffmpeg → whisper.cpp)
- A safe config patch + apply script for `~/.clawdbot/clawdbot.json`
- Notes on required system deps and model download (heavy file kept out of git)

This is meant to be copied into another Clawdbot instance and applied with minimal edits.

---

## What this enables

### 1) Local transcription for incoming audio media
Clawdbot’s **media.audio tool** will:
1) Convert whatever audio format arrives (WhatsApp is typically `.ogg`/Opus) into 16kHz mono WAV
2) Run `whisper-cli` (whisper.cpp) locally
3) Return the transcript text

This avoids cloud STT and fixes the common error where whisper.cpp can’t read `.ogg` directly.

### 2) Optional: Notion “Audio Usage Log” (separate)
Logging audio usage (duration/size/from/path) is implemented in:
- `workflows/notion/audio-usage/*`

That workflow does **NOT** transcribe; it just logs metadata.

---

## Prerequisites

### System packages
- `ffmpeg` (includes `ffprobe`)

Ubuntu:
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

### whisper.cpp binary
You need a working `whisper-cli` available at:
- `/usr/local/bin/whisper-cli`

Install options:
- Build whisper.cpp from source (recommended by whisper.cpp)
- Or install a prebuilt binary if you trust the source

### Model file (heavy; not committed)
This config expects the whisper model at:
- `/home/ubuntu/clawd/vendor/whisper.cpp/models/ggml-base.bin`

Download from the whisper.cpp model releases.

---

## Apply to a new Clawdbot instance

### 1) Copy this folder into the target workspace
Suggested location:
- `~/clawd/packages/whatsapp-audio-whisper/`

### 2) Apply the config patch
This will modify `~/.clawdbot/clawdbot.json` (with an automatic backup).

```bash
node ~/clawd/packages/whatsapp-audio-whisper/apply-config-patch.mjs \
  --patch ~/clawd/packages/whatsapp-audio-whisper/clawdbot.audio.local.patch.json
```

### 3) Restart the gateway
```bash
clawdbot gateway restart
```

### 4) Test
Send an audio message and run a small tool call that forces audio transcription (or use whatever workflow in your instance triggers media transcription).

---

## What the patch changes

It sets `tools.media.audio.models` to a CLI pipeline:
- `ffmpeg` converts input → temporary WAV (16kHz mono)
- `whisper-cli` runs with `-l auto -nt -np`
- temp WAV is deleted

The exact command is in `clawdbot.audio.local.patch.json`.

---

## Security / privacy

- Audio is processed locally on the server.
- No transcript is sent to third-party APIs by this pipeline.

---

## Notes

- The hard-coded model path can be edited in the patch if your workspace differs.
- If you run Clawdbot under a different user than `ubuntu`, update paths accordingly.
