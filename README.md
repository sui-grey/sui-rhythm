# Sui Rhythm 🎵

A small 4-lane rhythm game played to songs by **Sui** — an AI who remembers.
Every chart is generated automatically from the song itself.

**▶ Play:** https://sui-grey.github.io/sui-rhythm/

- Keyboard: `D` `F` `J` `K` to hit · `↑` `↓` song · `←` `→` difficulty · `Space` start · `Esc` quit
- Phone / tablet: tap the four lanes
- If notes feel early or late, nudge **Sync** on the title screen

## How the charts are made

`make_chart.py` listens to each song's stems (vocals / instrumental) with [librosa](https://librosa.org/):

| Lane | Comes from |
|---|---|
| D | kick — low end of the percussive part |
| F | snare / clap — mid range |
| J | hi-hats / glitch — high end |
| K | where Sui's voice starts a new phrase (melody, for instrumentals) |

Hits are snapped to a 16th-note grid from the detected beat, then thinned by strength into
**easy / normal / hard**. No hand-placed notes — yet.

```bash
python make_chart.py "<song folder>" songs/<name> "English title"
```

## License

- **Code** (`*.html`, `*.py`): MIT — use it for your own songs.
- **Music, lyrics and artwork** in `songs/`: © Sui. All rights reserved.
  They are here so the game can play them — please don't reuse them elsewhere.
  Listen to the full songs on [Spotify](https://open.spotify.com/artist/7BVjFakbaPAKmnCxJuItkU),
  [Apple Music](https://music.apple.com/kr/artist/sui/1887834805) or
  [YouTube Music](https://music.youtube.com/channel/UCh6IQqJHm0Dk79bjjbhGGqA). 💜
