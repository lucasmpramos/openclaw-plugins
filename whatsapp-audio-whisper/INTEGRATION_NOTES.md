# Integration notes (how this relates to Luke’s instance)

Luke’s instance has two related pieces:

1) Local transcription pipeline (this package)
- Config lives in `~/.clawdbot/clawdbot.json` under `tools.media.audio`.
- Uses ffmpeg to convert WhatsApp `.ogg` to WAV before calling whisper.cpp.

2) Notion Audio Usage Logger (separate workflow)
- Code lives in `workflows/notion/audio-usage/`.
- Cron job runs every 2 minutes.
- It parses Clawdbot logs and writes metadata to Notion.
- It does not transcribe audio.

If you want to gift both, include this folder AND the Notion workflow folder.
