# clawdbot-plugins

My custom Clawdbot plugins and workflows.

## Plugins

### [whatsapp-audio-whisper](./whatsapp-audio-whisper)

Local audio transcription for WhatsApp using whisper.cpp. No cloud APIs needed.

- Converts .ogg/Opus → WAV → transcript
- Config patch for Clawdbot
- Includes audio usage tracker for Notion

### [notion-whatsapp-logger](./notion-whatsapp-logger)

Logs WhatsApp conversations to Notion with daily organization.

- Inbound/outbound message logging
- Daily pages per contact
- Queue-based batching
