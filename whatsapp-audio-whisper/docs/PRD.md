# PRD: WhatsApp Audio Transcription

**Version:** 1.0
**Last Updated:** 2026-01-29
**Author:** Bob (AI Agent)
**Status:** ✅ Production

---

## 1. Overview

### 1.1 Purpose
Automatically transcribe WhatsApp voice messages using local Whisper (whisper.cpp), enabling:
- Searchable audio content
- No cloud API costs
- Fast local processing
- Integration with WhatsApp logging system

### 1.2 Key Features
- ✅ Local transcription (no external API)
- ✅ Multiple language support (auto-detect)
- ✅ Fast processing (~10s for 1 min audio)
- ✅ Integration with Clawdbot gateway

---

## 2. Architecture

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLAWDBOT GATEWAY                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                      ┌──────────────────────┐ │
│  │  WhatsApp   │  audio message       │   Audio Processor    │ │
│  │   Channel   │ ──────────────────▶  │                      │ │
│  └─────────────┘                      │  1. Save .ogg file   │ │
│                                       │  2. Convert to .wav  │ │
│                                       │  3. Run whisper-cli  │ │
│                                       │  4. Return transcript│ │
│                                       └──────────┬───────────┘ │
│                                                  │              │
│                                                  ▼              │
│                                       ┌──────────────────────┐ │
│                                       │  Agent receives msg  │ │
│                                       │  with transcript     │ │
│                                       └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Components

| Component | Location | Purpose |
|-----------|----------|---------|
| whisper.cpp | `/home/ubuntu/clawd/vendor/whisper.cpp/` | Local speech-to-text engine |
| whisper-cli | `/usr/local/bin/whisper-cli` | CLI wrapper for whisper.cpp |
| Model | `vendor/whisper.cpp/models/ggml-base.bin` | Whisper base model (~150MB) |
| ffmpeg | System package | Audio format conversion |

### 2.3 Processing Flow

```
1. WhatsApp audio arrives (.ogg format)
2. Saved to: ~/.clawdbot/media/inbound/{uuid}.ogg
3. Gateway audio processor triggered
4. ffmpeg converts: .ogg → .wav (16kHz mono)
5. whisper-cli transcribes: .wav → text
6. Transcript appended to message body
7. Agent receives: "[Audio]\nUser text: <media:audio>\nTranscript: {text}"
```

---

## 3. Installation

### 3.1 Prerequisites

```bash
# Install ffmpeg
sudo apt-get install ffmpeg

# Install build tools
sudo apt-get install build-essential cmake
```

### 3.2 Build whisper.cpp

```bash
# Clone repository
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Build
make

# Download model (base recommended for balance of speed/quality)
bash ./models/download-ggml-model.sh base

# Install CLI
sudo cp main /usr/local/bin/whisper-cli
```

### 3.3 Verify Installation

```bash
# Test transcription
whisper-cli -m models/ggml-base.bin -l auto test.wav
```

---

## 4. Configuration

### 4.1 Gateway Config (`~/.clawdbot/clawdbot.json`)

```json
{
  "tools": {
    "media": {
      "audio": {
        "enabled": true,
        "models": [
          {
            "type": "cli",
            "command": "bash",
            "args": [
              "-lc",
              "set -euo pipefail; in=\"{{MediaPath}}\"; tmp=$(mktemp --suffix=.wav); ffmpeg -y -i \"$in\" -ar 16000 -ac 1 -vn \"$tmp\" >/dev/null 2>&1; /usr/local/bin/whisper-cli -m /home/ubuntu/clawd/vendor/whisper.cpp/models/ggml-base.bin -l auto -nt -np \"$tmp\" 2>/dev/null; rm -f \"$tmp\""
            ],
            "timeoutSeconds": 240
          }
        ]
      }
    }
  }
}
```

### 4.2 Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `-m` | Model path | Required |
| `-l` | Language (auto/en/pt/etc) | auto |
| `-nt` | No timestamps in output | Enabled |
| `-np` | No progress bar | Enabled |
| `-t` | Thread count | CPU cores |

### 4.3 Model Selection

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| tiny | 75MB | Fastest | Basic |
| base | 142MB | Fast | Good |
| small | 466MB | Medium | Better |
| medium | 1.5GB | Slow | Best |

Recommended: `base` for most use cases.

---

## 5. Integration with WhatsApp Logger

### 5.1 The Challenge

The `message_received` hook fires BEFORE transcription completes:
- Hook sees: `<media:audio>`
- Transcript available only after Whisper runs
- Agent receives full transcript

### 5.2 The Solution

1. Plugin skips audio messages (doesn't log `<media:audio>`)
2. Agent receives message WITH transcript
3. Agent queues transcript with 🎤 prefix and original timestamp
4. Worker processes queue → Notion

### 5.3 Agent Procedure

When receiving audio with transcript:
```bash
node /home/ubuntu/clawd/workflows/whatsapp/logs-daily/queue-logger.mjs \
  --direction in \
  --phone "{phone}" \
  --text "🎤 {transcript}" \
  --time "{original_timestamp}"
```

---

## 6. Performance

### 6.1 Benchmarks (ggml-base model)

| Audio Length | Processing Time | Memory |
|--------------|-----------------|--------|
| 10 seconds | ~2s | ~500MB |
| 1 minute | ~10s | ~500MB |
| 5 minutes | ~45s | ~500MB |

### 6.2 Optimization Tips

- Use `tiny` model for fastest processing (lower quality)
- Increase `-t` threads on multi-core systems
- Keep audio files short when possible

---

## 7. Troubleshooting

### 7.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "model not found" | Wrong path | Check `-m` argument |
| "ffmpeg not found" | Not installed | `apt install ffmpeg` |
| Slow transcription | Large model | Use `base` or `tiny` |
| Wrong language | Auto-detect failed | Specify `-l pt` or `-l en` |

### 7.2 Debug Commands

```bash
# Check whisper installation
whisper-cli --help

# Test audio conversion
ffmpeg -i input.ogg -ar 16000 -ac 1 output.wav

# Test transcription
whisper-cli -m model.bin -l auto test.wav

# Check gateway logs
grep "audio" /tmp/clawdbot/clawdbot-*.log | tail -20
```

---

## 8. Security Considerations

- Audio files stored locally (no cloud upload)
- Temporary .wav files deleted after processing
- No API keys required
- Model runs entirely on-device

---

## 9. Future Improvements

- [ ] GPU acceleration (CUDA support)
- [ ] Streaming transcription
- [ ] Speaker diarization
- [ ] Custom fine-tuned models

---

## 10. References

- whisper.cpp: https://github.com/ggerganov/whisper.cpp
- OpenAI Whisper: https://github.com/openai/whisper
- ffmpeg: https://ffmpeg.org/

---

**System Owner:** Luke
**Implemented By:** Bob (AI Agent)
