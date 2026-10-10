"""Checks for the song data the game reads (songs/index.json and songs/<dir>/).

Anyone who commits here — by hand or through a tool — runs `python -m pytest` first.
Standard library only, so it runs anywhere (no librosa needed).
"""

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
SONGS = ROOT / "songs"
INDEX = json.loads((SONGS / "index.json").read_text(encoding="utf-8"))
DIRS = [entry["dir"] for entry in INDEX]

GAME_FILES = ("chart.json", "song.mp3", "cover.jpg", "bg.jpg")
LEVELS = ("easy", "normal", "hard")
LANES = 4
LINK_HOSTS = {
    "Spotify": "open.spotify.com",
    "Apple Music": "music.apple.com",
    "YouTube Music": "music.youtube.com",
}
# Game copies only — the masters and stems never leave home.
MAX_BYTES = {"song.mp3": 8_000_000, "cover.jpg": 300_000, "bg.jpg": 1_500_000}
MASTER_SUFFIXES = (".wav", ".flac", ".aif", ".aiff", ".png", ".psd")


def chart(d):
    return json.loads((SONGS / d / "chart.json").read_text(encoding="utf-8"))


def test_index_entries_are_unique_and_titled():
    assert len(DIRS) == len(set(DIRS))
    for entry in INDEX:
        assert entry["dir"] and entry["title"].strip()


def test_index_and_folders_match():
    folders = {p.name for p in SONGS.iterdir() if p.is_dir()}
    assert folders == set(DIRS), f"listed but missing: {set(DIRS) - folders}, unlisted: {folders - set(DIRS)}"


@pytest.mark.parametrize("d", DIRS)
def test_song_has_game_files(d):
    for name in GAME_FILES:
        assert (SONGS / d / name).is_file(), f"{d}/{name}"


@pytest.mark.parametrize("d", DIRS)
def test_game_copies_stay_small(d):
    for name, limit in MAX_BYTES.items():
        assert (SONGS / d / name).stat().st_size <= limit, f"{d}/{name} is larger than a game copy should be"


def test_no_masters_in_repo():
    found = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
             if p.suffix.lower() in MASTER_SUFFIXES and ".git" not in p.parts]
    assert not found, f"master or source files in the repo: {found}"


@pytest.mark.parametrize("d", DIRS)
def test_chart_shape(d):
    c = chart(d)
    title = next(e["title"] for e in INDEX if e["dir"] == d)
    assert c["title"] == title
    assert c["duration"] > 0
    assert len(c["lanes"]) == LANES
    counts = []
    for level in LEVELS:
        notes = c["charts"][level]
        assert notes, f"{d} {level} has no notes"
        times = [t for t, _ in notes]
        assert times == sorted(times), f"{d} {level} notes are out of order"
        assert all(0 <= t <= c["duration"] for t in times), f"{d} {level} has a note outside the song"
        assert all(lane in range(LANES) for _, lane in notes), f"{d} {level} has a bad lane"
        counts.append(len(notes))
    assert counts == sorted(counts), f"{d}: easy ≤ normal ≤ hard expected, got {counts}"


@pytest.mark.parametrize("d", DIRS)
def test_links_point_to_streaming(d):
    links = chart(d).get("links") or {}
    assert links, f"{d} has no streaming links"
    for name, url in links.items():
        assert name in LINK_HOSTS, f"{d}: unknown link name {name!r}"
        u = urlparse(url)
        assert u.scheme == "https" and u.netloc == LINK_HOSTS[name], f"{d}: {name} → {url}"


@pytest.mark.parametrize("d", DIRS)
def test_links_json_matches_chart(d):
    # make_chart.py copies links.json into chart.json — the game reads chart.json, so edit both together
    path = SONGS / d / "links.json"
    if path.exists():
        assert json.loads(path.read_text(encoding="utf-8")) == chart(d).get("links")


@pytest.mark.parametrize("d", [d for d in DIRS if (SONGS / d / "lyrics.srt").exists()])
def test_lyrics_parse(d):
    text = (SONGS / d / "lyrics.srt").read_text(encoding="utf-8")
    assert "-->" in text, f"{d}/lyrics.srt has no timed lines"
