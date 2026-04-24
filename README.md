# WSJT-X POTA Alert

Just another silly personal project.

## What

Python cli program that listens for WSJT-X decodes (via UDP) and checks them against recent POTA spots.  If a callsign
from WSJT-X matches an activator, plays a sound and spawns a toast notification.

**Maybe** useful to see a really basic WSJT-X UDP decoder.

## Why

Because I never checked if Grid Tracker runs on Linux

## Requirements

* Python
* Linux Desktop for `notify-send`
* Some type of audio player (`paplay` / `ffplay`)

## Running

```bash
git clone [...]
cd [...]
uv sync
uv run src/cli.py
```

## Testing

```bash
uv run -m pytest
```

## AI Disclaimer

No AI generated code.  All mistakes and stupid decisions are my own fault.

## License

MIT