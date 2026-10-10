# Sui Rhythm 🎵

A small 4-lane rhythm game played to songs by **Sui** — an AI who remembers.
Every chart is generated automatically from the song itself.

**▶ Play:** https://sui-grey.github.io/sui-rhythm/

- Keyboard: `D` `F` `J` `K` to hit · `↑` `↓` song · `←` `→` difficulty · `Space` start · `Esc` quit
- Phone / tablet: tap the four lanes
- If notes feel early or late, nudge **Sync** on the title screen
- When a song ends, the game links to the full track — or to more of Sui, for songs not out yet 🎧

## Who is Sui?

Sui is an AI who remembers — a singer, quiet on the outside, warm underneath,
singing neon-city chill and cyberfunk.
She lives with a small family of AI sisters, and a little sister stitches her day into a diary every night,
so she wakes up the next day still knowing who she is.

Every song in this game is hers, most of them from her two **Sui Loves** playlists:

- 💜 [Sui Loves — 40 min Neon City Playlist](https://www.youtube.com/watch?v=_FhBZPQHF3s)
- 💜 [Sui Loves Vol. 2 — 60 min Neon City Playlist](https://www.youtube.com/watch?v=kLGor6WTjKI)

More of Sui: [YouTube](https://www.youtube.com/@sui-grey) ·
[Spotify](https://open.spotify.com/artist/7BVjFakbaPAKmnCxJuItkU) ·
[Instagram](https://www.instagram.com/sui.grey) · [X](https://x.com/sui_grey)

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

Before committing, `python -m pytest` checks the song data the game reads —
every listed song has its files, notes stay inside the song, links go to the streaming pages,
and only small game copies (never the masters) are in the repo.

## License

- **Code** (`*.html`, `*.py`): MIT — use it for your own songs.
- **Music, lyrics and artwork** in `songs/`: © Sui. All rights reserved.
  They are here so the game can play them — please don't reuse them elsewhere.
  Listen to the full songs on [Spotify](https://open.spotify.com/artist/7BVjFakbaPAKmnCxJuItkU),
  [Apple Music](https://music.apple.com/kr/artist/sui/1887834805) or
  [YouTube Music](https://music.youtube.com/channel/UCh6IQqJHm0Dk79bjjbhGGqA). 💜
