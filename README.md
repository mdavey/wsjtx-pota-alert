# WSJTx POTA Alert

Just another silly personal project.  

**Maybe** useful to see a really basic WSJTx UDP decoder.

## What

A python console program that listens for WSJTx decodes (via UDP), checks them against recent POTA spots, and notifies 
the user if one pops up.

## Why

Because I never checked if GridTrack runs on Linux

## How

* Python
* Linux Desktop for `notify-send`
* Pulse Audio for `paplay`

## Testing

About time...

```bash
uv run -m pytest
```

## License

MIT