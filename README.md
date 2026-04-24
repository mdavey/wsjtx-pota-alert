# WSJT-X POTA Alert

Just another silly personal project.

## What

Python cli program that listens for WSJT-X decodes (via UDP) and checks them against recent POTA spots.  If a callsign
from WSJT-X matches an activator, plays a sound and spawns a toast notification.

**Maybe** useful as an example of a really basic WSJT-X UDP decoder.

Otherwise, set your expectations very low.

## Why

Because I never checked if Grid Tracker runs on Linux

## Requirements

* Python
* Linux Desktop for `notify-send`
* Some type of audio player (`paplay` / `ffplay`)

## Running

```bash
git clone https://github.com/mdavey/wsjtx-pota-alert.git
cd wsjtx-pota-alert
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