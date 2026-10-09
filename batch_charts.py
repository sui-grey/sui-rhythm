"""플레이리스트 통째로 채보 뽑기 — Sui Loves 1·2집 (10/10 새벽)

곡 이름은 sui-hub 플레이리스트(DB 곡 번호 → 영어 제목)에서, 폴더는 C:/sui/youtube/음악/<폴더>.
끝나면 songs/index.json을 1집 → 2집 → 그 밖 순서로 다시 쓴다.
사용: python batch_charts.py sui_loves sui_loves_2
"""
import json
import os
import re
import sys
import traceback

sys.path.insert(0, r"C:\sui\sui-hub\cli")
from commands.live.play import load_playlist         # noqa: E402
from commands.playlists import playlist_tracks       # noqa: E402

import make_chart                                     # noqa: E402

MUSIC = r"C:\sui\youtube\음악"
HERE = os.path.dirname(os.path.abspath(__file__))


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "song"


def main(names):
    order, failed = [], []
    idx_path = os.path.join(HERE, "songs", "index.json")
    try:   # 이미 있는 곡은 그 폴더 그대로(곡별 links.json이 거기 있다)
        known = {s["title"]: s["dir"] for s in json.load(open(idx_path, encoding="utf-8"))}
    except (OSError, ValueError):
        known = {}
    for name in names:
        pl = load_playlist(name)
        for t in playlist_tracks(list(pl.get("songs", []))):
            d = known.get(t["title"]) or slug(t["title"])
            print(f"\n=== {t['title']}  ({t['folder']}) → songs/{d}", flush=True)
            try:
                make_chart.main(os.path.join(MUSIC, t["folder"]), os.path.join(HERE, "songs", d), t["title"])
                order.append(d)
            except (Exception, SystemExit) as e:
                failed.append((t["title"], str(e)))
                traceback.print_exc()
    idx_path = os.path.join(HERE, "songs", "index.json")
    songs = json.load(open(idx_path, encoding="utf-8"))
    by_dir = {s["dir"]: s for s in songs}
    ordered = [by_dir[d] for d in order if d in by_dir] + [s for s in songs if s["dir"] not in order]
    json.dump(ordered, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n끝: {len(order)}곡, 실패 {len(failed)}곡", failed)


if __name__ == "__main__":
    main(sys.argv[1:])
