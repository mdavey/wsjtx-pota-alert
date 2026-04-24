# WSJTx POTA Alert

Just another silly personal project.  

**Maybe** useful to see a really basic WSJT-X UDP decoder.

## What

A python console program that listens for WSJT-X decodes (via UDP), checks them against recent POTA spots, and notifies 
the user if one pops up.

## Why

Because I never checked if GridTrack runs on Linux

## How

* Python
* Linux Desktop for `notify-send`
* Some type of audio player (`paplay` / `ffplay`)

## Testing

About time...

```bash
uv run -m pytest
```

## License

MIT